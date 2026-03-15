from app import app, render_template, db, admin_required, permission_required
from flask import request, make_response
import csv
import io
from models.companion_profiles import CompanionProfile, VerificationStatusEnum
from models.bookings import Booking, BookingStatusEnum
from models.payments import Payment, PaymentStatusEnum
from models.users import User
from models.customer_profiles import CustomerProfile
from datetime import datetime, timedelta
from sqlalchemy import func, desc
import json

@app.get('/admin/analytics')
@admin_required
@permission_required('analytics:view')
def analytics():
    # Time range filter
    range_type = request.args.get('range', '90')  # Default 90 days
    now = datetime.now()
    
    if range_type == '7':
        start_date = now - timedelta(days=7)
        group_by_format = '%Y-%m-%d'
    elif range_type == '30':
        start_date = now - timedelta(days=30)
        group_by_format = '%Y-%m-%d'
    elif range_type == '12m':
        start_date = now - timedelta(days=365)
        group_by_format = '%Y-%m'
    else:
        start_date = now - timedelta(days=90)
        group_by_format = '%Y-%m-%d'

    # Key Metrics
    total_revenue = db.session.query(func.sum(Payment.amount)).filter(
        Payment.status == PaymentStatusEnum.PAID,
        Payment.paid_at >= start_date
    ).scalar() or 0
    
    total_bookings = Booking.query.filter(
        Booking.start_time >= start_date
    ).count()
    
    new_users = User.query.filter(
        User.created_at >= start_date
    ).count()
    
    # Conversion Rate
    completed_bookings = Booking.query.filter(
        Booking.status == BookingStatusEnum.COMPLETED,
        Booking.start_time >= start_date
    ).count()
    
    conversion_rate = round((completed_bookings / total_bookings * 100), 1) if total_bookings > 0 else 0
    
    # Revenue Trend Data (Daily/Monthly)
    revenue_trend_raw = db.session.query(
        func.strftime(group_by_format, Payment.paid_at).label('period'),
        func.sum(Payment.amount).label('total')
    ).filter(
        Payment.status == PaymentStatusEnum.PAID,
        Payment.paid_at >= start_date
    ).group_by('period').order_by('period').all()
    
    revenue_labels = [r.period for r in revenue_trend_raw]
    revenue_values = [float(r.total) for r in revenue_trend_raw]
    
    # User Growth Trend
    user_growth_raw = db.session.query(
        func.strftime(group_by_format, User.created_at).label('period'),
        func.count(User.user_id).label('total')
    ).filter(
        User.created_at >= start_date
    ).group_by('period').order_by('period').all()
    
    user_labels = [u.period for u in user_growth_raw]
    user_values = [u.total for u in user_growth_raw]
    
    # Revenue Peaks
    peak_day_raw = db.session.query(
        func.strftime('%b %d', Payment.paid_at).label('day'),
        func.sum(Payment.amount).label('total')
    ).filter(
        Payment.status == PaymentStatusEnum.PAID,
        Payment.paid_at >= start_date
    ).group_by('day').order_by(desc('total')).first()
    
    lowest_day_raw = db.session.query(
        func.strftime('%b %d', Payment.paid_at).label('day'),
        func.sum(Payment.amount).label('total')
    ).filter(
        Payment.status == PaymentStatusEnum.PAID,
        Payment.paid_at >= start_date
    ).group_by('day').order_by('total').first()
    
    total_revenue = float(total_revenue)
    avg_per_day = total_revenue / int(range_type) if range_type.isdigit() else (total_revenue / 30)

    # Success Rate (Completed vs (Completed + Rejected/Cancelled))
    cancelled_bookings = Booking.query.filter(
        Booking.status == BookingStatusEnum.REJECTED,
        Booking.start_time >= start_date
    ).count()
    
    denominator = completed_bookings + cancelled_bookings
    success_rate = round((completed_bookings / denominator * 100), 1) if denominator > 0 else 0

    # Top Companions by Revenue
    top_companions_raw = db.session.query(
        CompanionProfile.display_name,
        func.count(Booking.booking_id).label('booking_count'),
        func.sum(Booking.total_price).label('revenue')
    ).join(Booking).filter(
        Booking.status == BookingStatusEnum.COMPLETED,
        Booking.start_time >= start_date
    ).group_by(CompanionProfile.companion_id).order_by(desc('revenue')).limit(5).all()
    
    top_companions = []
    for comp in top_companions_raw:
        top_companions.append({
            'name': comp.display_name,
            'bookings': comp.booking_count,
            'revenue': float(comp.revenue or 0)
        })
    
    # Geographic Distribution
    top_locations_raw = db.session.query(
        CustomerProfile.location,
        func.count(Booking.booking_id).label('booking_count')
    ).join(Booking).filter(
        Booking.start_time >= start_date
    ).group_by(CustomerProfile.location).order_by(desc('booking_count')).limit(5).all()

    max_bookings = top_locations_raw[0].booking_count if top_locations_raw else 1
    formatted_locations = []
    for loc in top_locations_raw:
        formatted_locations.append({
            'name': loc.location or 'Unknown',
            'count': loc.booking_count,
            'percent': int((loc.booking_count / max_bookings) * 100) if max_bookings > 0 else 0
        })

    # Pending count for sidebar
    pending_count = CompanionProfile.query.filter_by(verification_status=VerificationStatusEnum.PENDING).count()

    # Final defensive casting
    peak_day_formatted = None
    if peak_day_raw:
        peak_day_formatted = {'day': peak_day_raw.day, 'total': float(peak_day_raw.total)}
        
    lowest_day_formatted = None
    if lowest_day_raw:
        lowest_day_formatted = {'day': lowest_day_raw.day, 'total': float(lowest_day_raw.total)}

    return render_template(
        'admin/analytics.html',
        now=now,
        active_page='analytics',
        pending_count=pending_count,
        total_revenue=float(total_revenue),
        total_bookings=total_bookings,
        new_users=new_users,
        conversion_rate=float(conversion_rate),
        success_rate=float(success_rate),
        top_companions=top_companions,
        top_locations=formatted_locations,
        selected_range=range_type,
        revenue_labels=revenue_labels,
        revenue_values=revenue_values,
        user_labels=user_labels,
        user_values=user_values,
        peak_day=peak_day_formatted,
        lowest_day=lowest_day_formatted,
        avg_per_day=float(avg_per_day)
    )

@app.get('/admin/report/generate')
@admin_required
@permission_required('analytics:view')
def generate_report():
    report_type = request.args.get('report_type', 'daily')
    date_str = request.args.get('date')
    export_format = request.args.get('format', 'pdf')
    
    now = datetime.now()
    if not date_str:
        if report_type == 'yearly':
            date_str = str(now.year)
        elif report_type == 'monthly':
            date_str = now.strftime('%Y-%m')
        else:
            date_str = now.strftime('%Y-%m-%d')

    # Determine period range
    if report_type == 'yearly':
        try:
            year = int(date_str)
        except ValueError:
            year = now.year
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31, 23, 59, 59)
        period_label = f"Year {year}"
    elif report_type == 'monthly':
        try:
            year, month = map(int, date_str.split('-'))
        except ValueError:
            year, month = now.year, now.month
        start_date = datetime(year, month, 1)
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        end_date = next_month - timedelta(seconds=1)
        period_label = start_date.strftime('%B %Y')
    elif report_type == 'weekly':
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            target_date = now
        start_date = target_date - timedelta(days=target_date.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0)
        end_date = start_date + timedelta(days=6, hours=23, minutes=59, seconds=59)
        period_label = f"Week of {start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"
    else: # daily
        try:
            start_date = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            start_date = now
        start_date = start_date.replace(hour=0, minute=0, second=0)
        end_date = start_date.replace(hour=23, minute=59, second=59)
        period_label = start_date.strftime('%B %d, %Y')

    # Query bookings for the period
    bookings = Booking.query.filter(
        Booking.start_time >= start_date,
        Booking.start_time <= end_date,
        Booking.status == BookingStatusEnum.COMPLETED
    ).order_by(Booking.start_time).all()

    # Detailed totals
    total_revenue = sum(float(b.total_price) for b in bookings)
    total_seconds = sum((b.end_time - b.start_time).total_seconds() for b in bookings)
    total_hours = total_seconds / 3600
    avg_rate = total_revenue / total_hours if total_hours > 0 else 0

    if export_format == 'excel':
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Headers
        writer.writerow(['Report Type', report_type.capitalize()])
        writer.writerow(['Period', period_label])
        writer.writerow([])
        writer.writerow(['Booking ID', 'Companion', 'Customer', 'Start Time', 'End Time', 'Duration (Hrs)', 'Total Price ($)'])
        
        for b in bookings:
            duration = (b.end_time - b.start_time).total_seconds() / 3600
            companion = CompanionProfile.query.get(b.companion_id)
            customer = CustomerProfile.query.get(b.customer_id)
            writer.writerow([
                b.booking_id,
                companion.display_name if companion else 'N/A',
                customer.full_name if customer else 'N/A',
                b.start_time.strftime('%Y-%m-%d %H:%M'),
                b.end_time.strftime('%Y-%m-%d %H:%M'),
                round(duration, 2),
                float(b.total_price)
            ])
            
        writer.writerow([])
        writer.writerow(['TOTAL REVENUE', '', '', '', '', '', float(total_revenue)])
        writer.writerow(['TOTAL HOURS', '', '', '', '', '', round(total_hours, 1)])
        writer.writerow(['AVG RATE', '', '', '', '', '', round(avg_rate, 2)])
        
        output.seek(0)
        response = make_response(output.getvalue())
        filename = f"report_{report_type}_{date_str}.csv"
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        response.headers["Content-type"] = "text/csv"
        return response

    return render_template(
        'admin/report_print.html',
        type=report_type,
        period_label=period_label,
        bookings=bookings,
        total_revenue=total_revenue,
        total_hours=round(total_hours, 1),
        avg_rate=round(avg_rate, 2),
        title=f"{report_type.capitalize()} Report - {period_label}"
    )