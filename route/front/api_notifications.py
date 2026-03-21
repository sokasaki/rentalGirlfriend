from app import app, db
from flask import session, jsonify
from models.companion_profiles import CompanionProfile
from models.customer_profiles import CustomerProfile
from models.bookings import Booking, BookingStatusEnum
from models.users import User
from models.notifications import Notification
from models.reports import Report, ReportStatusEnum, TargetTypeEnum
from datetime import datetime

@app.get('/api/notifications/state')
def api_notifications_state():
    if not session.get('user_id'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = session.get('user_id')
    current_user = User.query.get(user_id)
    
    if not current_user:
        return jsonify({'error': 'User not found'}), 404

    companion = CompanionProfile.query.filter_by(user_id=user_id).first()
    customer = CustomerProfile.query.filter_by(user_id=user_id).first()
    
    user_type = None
    pending_bookings = []
    approved_bookings = []
    
    if companion:
        user_type = 'companion'
        pending_bookings_query = Booking.query.filter_by(
            companion_id=companion.companion_id,
            status=BookingStatusEnum.PENDING
        ).all()
        
        for booking in pending_bookings_query:
            customer_profile = CustomerProfile.query.get(booking.customer_id)
            pending_bookings.append({
                'booking_id': booking.booking_id,
                'customer_name': customer_profile.full_name if customer_profile else 'Anonymous',
                'start_time_display': booking.start_time.strftime('%b %d, %I:%M %p'),
                'amount': float(booking.total_price)
            })
            
    elif customer:
        user_type = 'customer'
        approved_bookings_query = Booking.query.filter_by(
            customer_id=customer.customer_id,
            status=BookingStatusEnum.APPROVED
        ).all()
        
        for booking in approved_bookings_query:
            companion_profile = CompanionProfile.query.get(booking.companion_id)
            approved_bookings.append({
                'booking_id': booking.booking_id,
                'companion_name': companion_profile.display_name if companion_profile else 'Unknown',
                'start_time_display': booking.start_time.strftime('%b %d, %I:%M %p'),
                'amount': float(booking.total_price)
            })

    # Fetch unread notifications
    unread_notifications = Notification.query.filter_by(
        user_id=user_id,
        is_read=False
    ).order_by(Notification.created_at.desc()).all()
    
    formatted_notifications = []
    for notif in unread_notifications[:10]: # Limit to 10 for payload size
        icon_type = 'info'
        if 'Approved' in notif.title or 'Successful' in notif.title:
            icon_type = 'success'
        elif 'Declined' in notif.title or 'Rejected' in notif.title or 'Failed' in notif.title:
            icon_type = 'danger'
            
        formatted_notifications.append({
            'notification_id': notif.notification_id,
            'title': notif.title,
            'message': notif.message,
            'created_at_display': notif.created_at.strftime('%b %d, %I:%M %p'),
            'icon_type': icon_type
        })
    
    # Pending reports
    pending_reports = []
    if companion:
        reports_query = Report.query.filter_by(
            target_id=user_id,
            status=ReportStatusEnum.AWAITING_INFO
        ).filter(
            Report.target_type == TargetTypeEnum.COMPANION
        ).all()
    else:
        reports_query = Report.query.filter_by(
            reporter_id=user_id,
            status=ReportStatusEnum.AWAITING_INFO
        ).all()
        
    for report in reports_query:
        pending_reports.append({
            'report_id': report.report_id,
            'reason': report.reason
        })

    notification_count = len(unread_notifications) + len(pending_bookings) + len(approved_bookings) + len(pending_reports)
    
    return jsonify({
        'success': True,
        'user_type': user_type,
        'notification_count': notification_count,
        'pending_bookings': pending_bookings,
        'approved_bookings': approved_bookings,
        'notifications': formatted_notifications,
        'pending_reports': pending_reports
    })
