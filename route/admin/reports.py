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
@permission_required('manage_reports')
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
@permission_required('manage_reports')
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
    if reporter_user:
        cp = CustomerProfile.query.filter_by(user_id=reporter_user.user_id).first()
        comp = CompanionProfile.query.filter_by(user_id=reporter_user.user_id).first()
        if cp:
            reporter_name = cp.full_name or reporter_user.email
            reporter_photo = cp.profile_photo
            reporter_type = 'Customer'
        elif comp:
            reporter_name = comp.display_name or reporter_user.email
            reporter_type = 'Companion'
        else:
            reporter_name = reporter_user.email

    # Resolve target
    target_user = None
    target_name = f'ID #{report.target_id}'
    target_photo = None
    target_type_label = report.target_type.value

    if report.target_type in (TargetTypeEnum.USER, TargetTypeEnum.COMPANION):
        target_user = User.query.get(report.target_id)
        if target_user:
            cp = CustomerProfile.query.filter_by(user_id=target_user.user_id).first()
            comp = CompanionProfile.query.filter_by(user_id=target_user.user_id).first()
            if cp:
                target_name = cp.full_name or target_user.email
                target_photo = cp.profile_photo
                target_type_label = 'Customer'
            elif comp:
                target_name = comp.display_name or target_user.email
                target_type_label = 'Companion'
            else:
                target_name = target_user.email
    elif report.target_type == TargetTypeEnum.BOOKING:
        from models.bookings import Booking
        booking = Booking.query.get(report.target_id)
        if booking:
            target_name = f'Booking #{report.target_id}'
            target_type_label = 'Booking'

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
        target_user=target_user,
        target_name=target_name,
        target_photo=target_photo,
        target_type_label=target_type_label,
        full_reason=full_reason,
        user_response=user_response,
    )


@app.post('/admin/resolve-report/<int:report_id>')
@admin_required
@permission_required('manage_reports')
def resolve_report(report_id):
    from models.reports import Report, ReportStatusEnum
    report = Report.query.get_or_404(report_id)
    report.status = ReportStatusEnum.RESOLVED
    db.session.commit()
    flash(f'Report #{report_id} has been marked as resolved.', 'success')
    return redirect(url_for('reports'))

@app.post('/admin/request-info/<int:report_id>')
@admin_required
@permission_required('manage_reports')
def request_info(report_id):
    from models.reports import Report, ReportStatusEnum, TargetTypeEnum
    report = Report.query.get_or_404(report_id)

    # Update report status
    report.status = ReportStatusEnum.AWAITING_INFO
    report.info_requested_at = datetime.utcnow()

    # Notify the TARGET (the person being reported)
    # target_id is now always a user_id for COMPANION and USER types
    if report.target_type in (TargetTypeEnum.COMPANION, TargetTypeEnum.USER):
        notify_user_id = report.target_id
    else:
        # Fallback for BOOKING type — notify reporter
        notify_user_id = report.reporter_id

    notification = Notification(
        user_id=notify_user_id,
        title="Response Required on Report",
        message=f"A report has been filed against you (Report #{report_id}). Admin has requested your response. Please provide details within 24 hours.",
        created_at=datetime.utcnow()
    )

    db.session.add(notification)
    db.session.commit()

    flash(f'Info requested for report #{report_id}. The reported user has been notified.', 'warning')
    return redirect(url_for('report_detail', report_id=report_id))

@app.post('/admin/ban-user/<int:user_id>')
@admin_required
@permission_required('manage_users')
def ban_user(user_id):
    user = User.query.get_or_404(user_id)
    user.status = UserStatus.BANNED
    db.session.commit()
    
    flash(f'User {user.email} has been banned.', 'danger')
    return redirect(request.referrer or url_for('reports'))

@app.get('/admin/export-report')
@admin_required
@permission_required('manage_reports')
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