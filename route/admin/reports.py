from app import app, render_template, db
from models.companion_profiles import CompanionProfile, VerificationStatusEnum
from models.customer_profiles import CustomerProfile
from models.users import User, UserStatus
from models.notifications import Notification
from flask import Response, request, redirect, url_for, flash
from app import admin_required, permission_required
import csv
import io
from datetime import datetime, timedelta

@app.get('/admin/reports')
@admin_required
@permission_required('report:view')
def reports():
    from models.reports import Report, ReportStatusEnum
    from models.users import User
    
    # Fetch all reports with reporter info
    reports_list = db.session.query(Report, User).join(User, Report.reporter_id == User.user_id).order_by(Report.created_at.desc()).all()
    
    # Calculate stats
    total_count = Report.query.count()
    pending_count = Report.query.filter_by(status=ReportStatusEnum.PENDING).count()
    awaiting_count = Report.query.filter_by(status=ReportStatusEnum.AWAITING_INFO).count()
    resolved_count = Report.query.filter_by(status=ReportStatusEnum.RESOLVED).count()
    
    return render_template(
        'admin/reports.html', 
        active_page='reports', 
        reports=reports_list,
        total_count=total_count,
        pending_count=pending_count,
        awaiting_count=awaiting_count,
        resolved_count=resolved_count
    )

@app.get('/admin/reports/<int:report_id>')
@admin_required
@permission_required('report:view')
def report_detail(report_id):
    from models.reports import Report, TargetTypeEnum
    from models.customer_profiles import CustomerProfile
    from models.companion_profiles import CompanionProfile

    report = Report.query.get_or_404(report_id)
    reporter_user = User.query.get(report.reporter_id)

    # Resolve reporter profile name
    reporter_name = 'Unknown'
    reporter_photo = None
    reporter_type = 'User'
    reporter_profile_id = None
    if reporter_user:
        cp = CustomerProfile.query.filter_by(user_id=reporter_user.user_id).first()
        comp = CompanionProfile.query.filter_by(user_id=reporter_user.user_id).first()
        if cp:
            reporter_name = cp.full_name or reporter_user.email
            reporter_photo = cp.main_url
            reporter_type = 'Customer'
            reporter_profile_id = reporter_user.user_id # view_customer takes user_id
        elif comp:
            reporter_name = comp.display_name or reporter_user.email
            reporter_photo = comp.primary_main_url
            reporter_type = 'Companion'
            reporter_profile_id = comp.companion_id # view_companion takes companion_id
        else:
            reporter_name = reporter_user.email

    # Resolve target
    target_user = None
    target_name = f'ID #{report.target_id}'
    target_photo = None
    target_type_label = report.target_type.value
    target_profile_id = None

    if report.target_type in (TargetTypeEnum.USER, TargetTypeEnum.COMPANION):
        target_user = User.query.get(report.target_id)
        if target_user:
            cp = CustomerProfile.query.filter_by(user_id=target_user.user_id).first()
            comp = CompanionProfile.query.filter_by(user_id=target_user.user_id).first()
            if cp:
                target_name = cp.full_name or target_user.email
                target_photo = cp.thumbnail_url
                target_type_label = 'Customer'
                target_profile_id = target_user.user_id # view_customer takes user_id
            elif comp:
                target_name = comp.display_name or target_user.email
                target_photo = comp.primary_thumbnail_url
                target_type_label = 'Companion'
                target_profile_id = comp.companion_id # view_companion takes companion_id
            else:
                target_name = target_user.email
    elif report.target_type == TargetTypeEnum.BOOKING:
        from models.bookings import Booking
        booking = Booking.query.get(report.target_id)
        if booking:
            target_name = f'Booking #{report.target_id}'
            target_type_label = 'Booking'

    # Stats
    reporter_history_count = Report.query.filter_by(reporter_id=report.reporter_id).count()
    target_history_count = Report.query.filter_by(target_id=report.target_id, target_type=report.target_type).count()

    # Split reason from user response
    full_reason = report.reason or ''
    user_response = None
    if '[USER RESPONSE]:' in full_reason:
        parts = full_reason.split('\n\n[USER RESPONSE]:', 1)
        full_reason = parts[0].strip()
        user_response = parts[1].strip() if len(parts) > 1 else None

    return render_template(
        'admin/report/report_detail.html',
        active_page='reports',
        report=report,
        reporter_user=reporter_user,
        reporter_name=reporter_name,
        reporter_photo=reporter_photo,
        reporter_type=reporter_type,
        reporter_profile_id=reporter_profile_id,
        target_user=target_user,
        target_name=target_name,
        target_photo=target_photo,
        target_type_label=target_type_label,
        target_profile_id=target_profile_id,
        reporter_history_count=reporter_history_count,
        target_history_count=target_history_count,
        full_reason=full_reason,
        user_response=user_response,
    )


@app.post('/admin/resolve-report/<int:report_id>')
@admin_required
@permission_required('report:manage')
def resolve_report(report_id):
    from models.reports import Report, ReportStatusEnum
    report = Report.query.get_or_404(report_id)
    report.status = ReportStatusEnum.RESOLVED
    db.session.commit()
    flash(f'Report #{report_id} has been marked as resolved.', 'success')
    return redirect(url_for('reports'))

@app.post('/admin/request-info/<int:report_id>')
@admin_required
@permission_required('report:manage')
def request_info(report_id):
    from models.reports import Report, ReportStatusEnum, TargetTypeEnum
    from models import Notification
    from flask import request, flash, redirect, url_for
    from extensions import db
    from datetime import datetime

    report = Report.query.get_or_404(report_id)
    request_target = request.form.get('request_target', 'subject') # 'reporter', 'subject', 'both'

    # Update report status
    report.status = ReportStatusEnum.AWAITING_INFO
    report.info_requested_at = datetime.utcnow()

    notify_ids = []
    if request_target == 'reporter':
        notify_ids.append(report.reporter_id)
    elif request_target == 'subject':
        if report.target_type in (TargetTypeEnum.COMPANION, TargetTypeEnum.USER):
            notify_ids.append(report.target_id)
        else:
            # Fallback for BOOKING type or others where target_id isn't a user
            notify_ids.append(report.reporter_id)
    elif request_target == 'both':
        notify_ids.append(report.reporter_id)
        if report.target_type in (TargetTypeEnum.COMPANION, TargetTypeEnum.USER):
            notify_ids.append(report.target_id)

    # Dedup and create notifications
    notify_ids = list(set(notify_ids))
    for uid in notify_ids:
        msg = f"A report requires your response (Report #{report_id}). Please provide details within 24 hours."
        if uid == report.reporter_id and request_target != 'subject':
            msg = f"Additional information is needed for your report (Report #{report_id}). Please provide more details to help our investigation."
        
        notification = Notification(
            user_id=uid,
            title="Action Required: Report Investigation",
            message=msg,
            created_at=datetime.utcnow()
        )
        db.session.add(notification)

    db.session.commit()

    flash(f'Info request sent to {request_target.capitalize()}.', 'warning')
    return redirect(url_for('report_detail', report_id=report_id))

@app.post('/admin/ban-user/<int:user_id>')
@admin_required
@permission_required('user:delete')
def ban_user(user_id):
    from models.users import User, UserStatus
    user = User.query.get_or_404(user_id)
    user.status = UserStatus.BANNED
    user.suspended_until = None
    db.session.commit()
    
    flash(f'User {user.email} has been permanently banned.', 'danger')
    return redirect(request.referrer or url_for('reports'))

@app.post('/admin/suspend-user/<int:user_id>')
@admin_required
@permission_required('user:manage')
def suspend_user(user_id):
    from models.users import User, UserStatus
    from datetime import datetime, timedelta
    
    user = User.query.get_or_404(user_id)
    duration_hours = request.form.get('duration', type=int)
    
    if duration_hours == -1:
        # Permanent ban
        user.status = UserStatus.BANNED
        user.suspended_until = None
        flash(f'User {user.email} has been permanently banned.', 'danger')
    else:
        user.status = UserStatus.SUSPENDED
        user.suspended_until = datetime.utcnow() + timedelta(hours=duration_hours)
        
        # Format duration for flash message
        if duration_hours >= 24:
            days = duration_hours // 24
            label = f"{days} day{'s' if days > 1 else ''}"
        else:
            label = f"{duration_hours} hour{'s' if duration_hours > 1 else ''}"
            
        flash(f'User {user.email} has been suspended for {label}.', 'warning')
    
    db.session.commit()
    return redirect(request.referrer or url_for('reports'))

@app.get('/admin/export-report')
@admin_required
@permission_required('report:view')
def export_report():
    range_type = request.args.get('range', '90')
    now = datetime.now()
    
    if range_type == '7':
        start_date = now - timedelta(days=7)
    elif range_type == '30':
        start_date = now - timedelta(days=30)
    elif range_type == '12m':
        start_date = now - timedelta(days=365)
    else:
        start_date = now - timedelta(days=90)

    # Fetch data for report
    bookings = db.session.query(Booking, CompanionProfile, CustomerProfile).join(
        CompanionProfile, Booking.companion_id == CompanionProfile.companion_id
    ).join(
        CustomerProfile, Booking.customer_id == CustomerProfile.customer_id
    ).filter(
        Booking.start_time >= start_date
    ).all()

    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['Booking ID', 'Date', 'Customer', 'Companion', 'Amount', 'Status', 'Location'])
    
    # Rows
    for booking, companion, customer in bookings:
        writer.writerow([
            booking.booking_id,
            booking.start_time.strftime('%Y-%m-%d %H:%M'),
            customer.full_name,
            companion.display_name,
            f"${booking.total_price}",
            booking.status.value,
            booking.meeting_location or 'N/A'
        ])

    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=platform_report_{range_type}days_{now.strftime('%Y%m%d')}.csv"}
    )