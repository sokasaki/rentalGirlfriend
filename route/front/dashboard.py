from app import app, render_template, db
from upload_service import save_image
from flask import session, redirect, url_for, request, flash
import os
from models.companion_profiles import CompanionProfile, VerificationStatusEnum
from models.bookings import Booking, BookingStatusEnum
from models.payments import Payment, PaymentStatusEnum
from models.reviews import Review
from models.customer_profiles import CustomerProfile, GenderEnum
from models.users import User
from models.companion_photos import CompanionPhoto
from models.favorites import Favorite
from sqlalchemy import func, extract, desc
from datetime import datetime, timedelta
import json
import uuid
from werkzeug.utils import secure_filename
from models.availability import Availability, DayOfWeekEnum

@app.get('/dashboard-customer')
def dashboard_customer():
    # Get user_id from session
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    # Get customer profile for logged-in user
    customer = db.session.query(CustomerProfile).filter_by(
        user_id=user_id
    ).first()
    
    # Check for pending info requests for reports (as reporter or target)
    from models.reports import Report, ReportStatusEnum, TargetTypeEnum
    from sqlalchemy import or_, and_
    awaiting_info_reports = Report.query.filter(
        Report.status == ReportStatusEnum.AWAITING_INFO,
        or_(
            and_(Report.target_type == TargetTypeEnum.USER, Report.target_id == user_id),
            Report.reporter_id == user_id
        )
    ).all()
    
    if not customer:
        return "Customer profile not found", 404
    
    # Get user info
    user = db.session.query(User).filter_by(user_id=customer.user_id).first()
    
    # Get customer bookings
    all_bookings = db.session.query(Booking, CompanionProfile).join(
        CompanionProfile, Booking.companion_id == CompanionProfile.companion_id
    ).filter(
        Booking.customer_id == customer.customer_id
    ).order_by(Booking.start_time.desc()).all()
    
    # Separate upcoming and past bookings
    now = datetime.now()
    upcoming_bookings = []
    past_bookings = []
    
    for booking, companion in all_bookings:
        # Use thumbnail for the list view
        photo_url = companion.primary_thumbnail_url if companion.photos else '/static/images/avatar-placeholder.jpg'
        
        duration_hours = (booking.end_time - booking.start_time).total_seconds() / 3600
        
        booking_data = {
            'booking_id': booking.booking_id,
            'companion_id': companion.companion_id,
            'companion_user_id': companion.user_id,
            'companion_name': companion.display_name,
            'companion_photo': photo_url,
            'companion_rating': float(companion.avg_rating) if companion.avg_rating else 0,
            'start_time': booking.start_time,
            'end_time': booking.end_time,
            'duration': duration_hours,
            'location': booking.meeting_location or 'Not specified',
            'amount': float(booking.total_price),
            'status': booking.status.value,
            'rejection_reason': booking.rejection_reason,
            'review': {
                'rating': booking.review.rating,
                'comment': booking.review.comment,
                'reply': booking.review.reply,
                'replied_at': booking.review.replied_at
            } if booking.review else None
        }
        
        if booking.start_time >= now:
            upcoming_bookings.append(booking_data)
        else:
            past_bookings.append(booking_data)
    
    # Get favorites
    favorites_query = db.session.query(Favorite, CompanionProfile).join(
        CompanionProfile, Favorite.companion_id == CompanionProfile.companion_id
    ).filter(
        Favorite.customer_id == customer.customer_id
    ).all()
    
    favorites = []
    for favorite, companion in favorites_query:
        # Use thumbnail for favorites list
        photo_url = companion.primary_thumbnail_url if companion.photos else '/static/images/avatar-placeholder.jpg'
        
        # Parse personality traits
        try:
            if isinstance(companion.personality_traits, str):
                personality_traits = json.loads(companion.personality_traits)
            else:
                personality_traits = companion.personality_traits or []
        except:
            personality_traits = []
        
        favorites.append({
            'companion_id': companion.companion_id,
            'companion_name': companion.display_name,
            'companion_photo': photo_url,
            'companion_rating': float(companion.avg_rating) if companion.avg_rating else 0,
            'rate_per_hour': float(companion.rate_per_hour),
            'personality_traits': personality_traits[:2],
            'total_bookings': db.session.query(func.count(Booking.booking_id)).filter(
                Booking.companion_id == companion.companion_id
            ).scalar() or 0,
            'total_reviews': db.session.query(func.count(Review.review_id)).join(
                Booking, Review.booking_id == Booking.booking_id
            ).filter(Booking.companion_id == companion.companion_id).scalar() or 0
        })
    
    # Get payment history
    payments_query = db.session.query(Payment, Booking, CompanionProfile).join(
        Booking, Payment.booking_id == Booking.booking_id
    ).join(
        CompanionProfile, Booking.companion_id == CompanionProfile.companion_id
    ).filter(
        Booking.customer_id == customer.customer_id,
        Payment.status == PaymentStatusEnum.PAID
    ).order_by(Payment.paid_at.desc()).all()
    
    payments = []
    for payment, booking, companion in payments_query:
        duration_hours = (booking.end_time - booking.start_time).total_seconds() / 3600
        payments.append({
            'payment_id': payment.payment_id,
            'booking_id': booking.booking_id,
            'date': payment.paid_at or booking.start_time,
            'companion_name': companion.display_name,
            'description': f'Companion Service - {int(duration_hours)} hours',
            'amount': float(payment.amount),
            'method': payment.method.value if payment.method else 'CARD',
            'status': payment.status.value
        })
    
    # Calculate statistics
    total_bookings = len(all_bookings)
    upcoming_count = len(upcoming_bookings)
    favorites_count = len(favorites)
    total_spent = sum([p['amount'] for p in payments])
    
    # Generate timeline activities (recent activities)
    timeline_activities = []
    
    # Add recent bookings to timeline
    for booking_data in (upcoming_bookings + past_bookings)[:5]:
        if booking_data['start_time'] < now and booking_data['status'] == 'COMPLETED':
            timeline_activities.append({
                'type': 'booking',
                'date': booking_data['start_time'].strftime('%b %d, %Y'),
                'raw_date': booking_data['start_time'],
                'status': booking_data['status'],
                'start_time': booking_data['start_time'].strftime('%I:%M %p'),
                'duration': f"{int(booking_data['duration'])} hours",
                'companion_name': booking_data['companion_name'],
                'companion_photo': booking_data['companion_photo'],
                'location': booking_data['location']
            })
    
    # Add recent favorites
    # Since Favorite model might not have created_at, we use now() as fallback or if we can get it from DB
    favorites_query_raw = db.session.query(Favorite, CompanionProfile).join(
        CompanionProfile, Favorite.companion_id == CompanionProfile.companion_id
    ).filter(
        Favorite.customer_id == customer.customer_id
    ).order_by(Favorite.favorite_id.desc()).limit(3).all()

    for fav, companion in favorites_query_raw:
        # Re-using the logic from the favorites list above but limited to 3
        # (Actually we already have 'favorites' list, but it doesn't have a date)
        timeline_activities.append({
            'type': 'favorite',
            'date': datetime.now().strftime('%b %d, %Y'),
            'raw_date': datetime.now(), # Fallback since we don't have created_at on Favorite model usually
            'companion_name': companion.display_name,
            'companion_photo': next((f"/static/{p.photo_url}" if not p.photo_url.startswith(('/', 'http')) else p.photo_url for p in companion.photos if p.is_primary), '/static/images/avatar-placeholder.jpg'),
            'companion_rating': float(companion.avg_rating) if companion.avg_rating else 0,
            'companion_bookings': len(companion.bookings),
            'personality_traits': json.loads(companion.personality_traits) if isinstance(companion.personality_traits, str) else (companion.personality_traits or []),
            'companion_id': companion.companion_id,
            'hourly_rate': float(companion.rate_per_hour)
        })
    
    # Add recent payments
    for p_data in payments[:3]:
        timeline_activities.append({
            'type': 'payment',
            'date': p_data['date'].strftime('%b %d, %Y') if isinstance(p_data['date'], datetime) else p_data['date'],
            'raw_date': p_data['date'] if isinstance(p_data['date'], datetime) else now,
            'amount': p_data['amount'],
            'companion_name': p_data['companion_name']
        })
    
    # Add recent notifications
    from models.notifications import Notification
    recent_notifications = Notification.query.filter_by(user_id=customer.user_id).order_by(Notification.created_at.desc()).limit(5).all()
    for entry in recent_notifications:
        timeline_activities.append({
            'type': 'notification',
            'date': entry.created_at.strftime('%b %d, %Y'),
            'raw_date': entry.created_at,
            'title': entry.title,
            'message': entry.message,
            'is_read': entry.is_read
        })
    
    # Sort timeline by raw_date descending
    timeline_activities.sort(key=lambda x: x.get('raw_date', now), reverse=True)
    
    # Prepare customer data
    customer_data = {
        'customer_id': customer.customer_id,
        'full_name': customer.full_name or 'Customer',
        'email': user.email if user else 'customer@email.com',
        'phone': user.phone or '+1 (555) 123-4567',
        'date_of_birth': customer.date_of_birth.strftime('%Y-%m-%d') if customer.date_of_birth else '',
        'gender': customer.gender.value if customer.gender else 'PREFER_NOT_TO_SAY',
        'location': customer.location or 'Not specified',
        'bio': customer.bio or '',
        'profile_photo': customer.main_url or '/static/images/avatar-placeholder.jpg',
        'cover_photo': (f"/static/{customer.cover_photo}" if customer.cover_photo and not customer.cover_photo.startswith(('/', 'http', '/static')) else customer.cover_photo),
        'member_since': user.created_at.strftime('%B %Y') if user and user.created_at else 'January 2023'
    }
    
    return render_template('front/pages/dashboard-customer.html',
        customer=customer_data,
        total_bookings=total_bookings,
        upcoming_count=upcoming_count,
        favorites_count=favorites_count,
        total_spent=total_spent,
        upcoming_bookings=upcoming_bookings[:10],
        past_bookings=past_bookings[:10],
        favorites=favorites,
        payments=payments[:10],
        timeline_activities=timeline_activities,
        awaiting_reports=awaiting_info_reports
    )

@app.post('/toggle-favorite/<int:companion_id>')
def toggle_favorite(companion_id):
    from flask import jsonify
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Please log in to save favorites.'}), 401

    customer = db.session.query(CustomerProfile).filter_by(user_id=user_id).first()
    if not customer:
        return jsonify({'success': False, 'message': 'Only customers can add favorites.'}), 403

    existing = Favorite.query.filter_by(
        customer_id=customer.customer_id,
        companion_id=companion_id
    ).first()

    if existing:
        db.session.delete(existing)
        db.session.commit()
        is_favorited = False
    else:
        new_fav = Favorite(customer_id=customer.customer_id, companion_id=companion_id)
        db.session.add(new_fav)
        db.session.commit()
        is_favorited = True

    # Return new total count for this customer
    count = Favorite.query.filter_by(customer_id=customer.customer_id).count()
    return jsonify({'success': True, 'is_favorited': is_favorited, 'count': count})

@app.post('/notifications/mark-read')
def mark_notifications_read():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Login required'}), 401
    
    from models.notifications import Notification
    Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'success': True})

@app.get('/notifications')
def notifications_page():
    from datetime import datetime
    return render_template('front/pages/notifications.html', now=datetime.utcnow())


@app.get('/receipt/<int:payment_id>')
def receipt(payment_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    customer = db.session.query(CustomerProfile).filter_by(user_id=user_id).first()
    if not customer:
        return "Customer profile not found", 404

    payment_data = db.session.query(Payment, Booking, CompanionProfile).join(
        Booking, Payment.booking_id == Booking.booking_id
    ).join(
        CompanionProfile, Booking.companion_id == CompanionProfile.companion_id
    ).filter(
        Payment.payment_id == payment_id,
        Booking.customer_id == customer.customer_id
    ).first()

    if not payment_data:
        return "Receipt not found", 404

    payment, booking, companion = payment_data
    duration_hours = (booking.end_time - booking.start_time).total_seconds() / 3600
    base_amount = float(booking.total_price)
    total_amount = float(payment.amount)
    service_fee = max(total_amount - base_amount, 0)

    return render_template(
        'front/pages/receipt.html',
        customer=customer,
        payment=payment,
        booking=booking,
        companion=companion,
        duration_hours=duration_hours,
        base_amount=base_amount,
        service_fee=service_fee,
        total_amount=total_amount
    )

def get_availability_week(companion_id):
    # Define the order and labels for the week
    days_config = [
        {'id': DayOfWeekEnum.MON, 'name': 'Monday', 'short': 'MON'},
        {'id': DayOfWeekEnum.TUE, 'name': 'Tuesday', 'short': 'TUE'},
        {'id': DayOfWeekEnum.WED, 'name': 'Wednesday', 'short': 'WED'},
        {'id': DayOfWeekEnum.THU, 'name': 'Thursday', 'short': 'THU'},
        {'id': DayOfWeekEnum.FRI, 'name': 'Friday', 'short': 'FRI'},
        {'id': DayOfWeekEnum.SAT, 'name': 'Saturday', 'short': 'SAT'},
        {'id': DayOfWeekEnum.SUN, 'name': 'Sunday', 'short': 'SUN'}
    ]
    
    # Fetch all availability records for this companion
    availability_records = Availability.query.filter_by(companion_id=companion_id).all()
    
    # Group by day
    availability_map = {}
    for record in availability_records:
        day_key = record.day_of_week
        if day_key not in availability_map:
            availability_map[day_key] = []
        availability_map[day_key].append({
            'start': record.start_time.strftime('%H:%M'),
            'end': record.end_time.strftime('%H:%M')
        })
    
    # Build final list
    availability_week = []
    for config in days_config:
        day_slots = availability_map.get(config['id'], [])
        availability_week.append({
            'day_name': config['name'],
            'short_name': config['short'],
            'is_available': len(day_slots) > 0,
            'slots': day_slots
        })
        
    return availability_week

@app.get('/dashboard-companion')
def dashboard_companion():
    # Get user_id from session
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    # Get companion profile for logged-in user
    companion = db.session.query(CompanionProfile).filter_by(
        user_id=user_id
    ).first()
    
    if not companion:
        return "Companion profile not found", 404
    
    # Use resized 800px main image for the dashboard banner
    photo_url = companion.primary_main_url or '/static/images/avatar-placeholder.jpg'
    
    # Check for pending info requests for reports (as reporter or target)
    from models.reports import Report, ReportStatusEnum, TargetTypeEnum
    from sqlalchemy import or_, and_
    awaiting_info_reports = Report.query.filter(
        Report.status == ReportStatusEnum.AWAITING_INFO,
        or_(
            and_(Report.target_type == TargetTypeEnum.COMPANION, Report.target_id == user_id),
            Report.reporter_id == user_id
        )
    ).all()

    # Get pending requests (bookings with PENDING status)
    pending_requests = db.session.query(Booking, CustomerProfile, User).join(
        CustomerProfile, Booking.customer_id == CustomerProfile.customer_id
    ).join(
        User, CustomerProfile.user_id == User.user_id
    ).filter(
        Booking.companion_id == companion.companion_id,
        Booking.status == BookingStatusEnum.PENDING
    ).all()
    
    # Format pending requests
    formatted_requests = []
    for booking, customer, user in pending_requests:
        duration_hours = (booking.end_time - booking.start_time).total_seconds() / 3600
        customer_photo = customer.thumbnail_url or 'https://i.pravatar.cc/40?img=' + str(booking.customer_id % 70)
        formatted_requests.append({
            'booking_id': booking.booking_id,
            'customer_name': customer.full_name or 'Anonymous',
            'customer_photo': customer_photo,
            'start_time': booking.start_time,
            'end_time': booking.end_time,
            'duration': duration_hours,
            'location': booking.meeting_location or 'Not specified',
            'amount': float(booking.total_price)
        })
    
    # Get confirmed bookings (APPROVED, PAID, COMPLETED)
    confirmed_bookings = db.session.query(Booking, CustomerProfile, User).join(
        CustomerProfile, Booking.customer_id == CustomerProfile.customer_id
    ).join(
        User, CustomerProfile.user_id == User.user_id
    ).filter(
        Booking.companion_id == companion.companion_id,
        Booking.status.in_([BookingStatusEnum.APPROVED, BookingStatusEnum.PAID, BookingStatusEnum.COMPLETED])
    ).order_by(Booking.start_time.desc()).limit(10).all()
    
    # Format confirmed bookings
    formatted_bookings = []
    for booking, customer, user in confirmed_bookings:
        duration_hours = (booking.end_time - booking.start_time).total_seconds() / 3600
        customer_photo = customer.thumbnail_url or 'https://i.pravatar.cc/40?img=' + str(booking.customer_id % 70)
        formatted_bookings.append({
            'booking_id': booking.booking_id,
            'customer_name': customer.full_name or 'Anonymous',
            'customer_photo': customer_photo,
            'customer_user_id': user.user_id,
            'start_time': booking.start_time,
            'end_time': booking.end_time,
            'duration': duration_hours,
            'location': booking.meeting_location or 'Not specified',
            'amount': float(booking.total_price),
            'status': booking.status.value
        })
    
    # Calculate total earnings (all time)
    total_earnings = db.session.query(func.sum(Booking.total_price)).filter(
        Booking.companion_id == companion.companion_id,
        Booking.status.in_([BookingStatusEnum.PAID, BookingStatusEnum.COMPLETED])
    ).scalar() or 0
    
    # Calculate this month's earnings
    current_month = datetime.now().month
    current_year = datetime.now().year
    monthly_earnings = db.session.query(func.sum(Booking.total_price)).filter(
        Booking.companion_id == companion.companion_id,
        Booking.status.in_([BookingStatusEnum.PAID, BookingStatusEnum.COMPLETED]),
        extract('month', Booking.start_time) == current_month,
        extract('year', Booking.start_time) == current_year
    ).scalar() or 0
    
    # Count total bookings
    total_bookings = db.session.query(func.count(Booking.booking_id)).filter(
        Booking.companion_id == companion.companion_id
    ).scalar() or 0
    
    # Count this month's bookings
    monthly_bookings = db.session.query(func.count(Booking.booking_id)).filter(
        Booking.companion_id == companion.companion_id,
        extract('month', Booking.start_time) == current_month,
        extract('year', Booking.start_time) == current_year
    ).scalar() or 0
    
    # Get reviews
    reviews = db.session.query(Review, Booking, CustomerProfile, User).join(
        Booking, Review.booking_id == Booking.booking_id
    ).join(
        CustomerProfile, Booking.customer_id == CustomerProfile.customer_id
    ).join(
        User, CustomerProfile.user_id == User.user_id
    ).filter(
        Booking.companion_id == companion.companion_id
    ).order_by(Review.created_at.desc()).limit(10).all()
    
    # Format reviews
    formatted_reviews = []
    for review, booking, customer, user in reviews:
        formatted_reviews.append({
            'review_id': review.review_id,
            'customer_name': customer.full_name or 'Anonymous',
            'customer_photo': 'https://i.pravatar.cc/40?img=' + str(booking.customer_id % 70),
            'rating': review.rating,
            'comment': review.comment,
            'reply': review.reply,
            'replied_at': review.replied_at,
            'created_at': review.created_at,
            'date': review.created_at
        })
    
    # Calculate total review count
    total_reviews = db.session.query(func.count(Review.review_id)).join(
        Booking, Review.booking_id == Booking.booking_id
    ).filter(
        Booking.companion_id == companion.companion_id
    ).scalar() or 0
    
    # Calculate performance stats
    # Response rate (placeholder - would need a messages table)
    response_rate = 98
    
    # Acceptance rate
    total_requests = db.session.query(func.count(Booking.booking_id)).filter(
        Booking.companion_id == companion.companion_id,
        Booking.status.in_([BookingStatusEnum.PENDING, BookingStatusEnum.APPROVED, BookingStatusEnum.REJECTED])
    ).scalar() or 1
    
    accepted_requests = db.session.query(func.count(Booking.booking_id)).filter(
        Booking.companion_id == companion.companion_id,
        Booking.status == BookingStatusEnum.APPROVED
    ).scalar() or 0
    
    acceptance_rate = int((accepted_requests / total_requests) * 100) if total_requests > 0 else 0
    
    # Completion rate
    completed_bookings = db.session.query(func.count(Booking.booking_id)).filter(
        Booking.companion_id == companion.companion_id,
        Booking.status == BookingStatusEnum.COMPLETED
    ).scalar() or 0
    
    completion_rate = int((completed_bookings / total_bookings) * 100) if total_bookings > 0 else 0
    
    # Parse personality traits
    try:
        if isinstance(companion.personality_traits, str):
            personality_traits = json.loads(companion.personality_traits)
        else:
            personality_traits = companion.personality_traits or []
    except:
        personality_traits = []
    
    # Parse languages
    try:
        if isinstance(companion.languages, str):
            languages = json.loads(companion.languages)
        else:
            languages = companion.languages or ['English']
    except:
        languages = ['English']
    
    # Parse location
    location_parts = (companion.location or '').split(',')
    city = location_parts[0].strip() if len(location_parts) > 0 else ''
    state = location_parts[1].strip() if len(location_parts) > 1 else ''
    
    # Get current time for filtering and timeline
    today = datetime.now()
    
    # Sort formatted reviews by date for timeline
    sorted_reviews = sorted(formatted_reviews, key=lambda x: x['date'], reverse=True)
    
    # Generate timeline activities (recent activities)
    timeline_activities = []
    
    # Add pending requests to timeline
    for req in formatted_requests[:3]:
        timeline_activities.append({
            'type': 'request',
            'date': req['start_time'].strftime('%b %d, %Y'),
            'raw_date': req['start_time'],
            'customer_name': req['customer_name'],
            'duration': f"{int(req['duration'])} hours",
            'amount': req['amount'],
            'location': req['location']
        })
    
    # Add confirmed/recent bookings to timeline
    for booking in formatted_bookings[:5]:
        timeline_activities.append({
            'type': 'booking',
            'date': booking['start_time'].strftime('%b %d, %Y'),
            'raw_date': booking['start_time'],
            'status': booking['status'],
            'customer_name': booking['customer_name'],
            'customer_photo': booking['customer_photo'],
            'duration': f"{int(booking['duration'])} hours",
            'location': booking['location']
        })
    
    # Add recent reviews to timeline
    for review in sorted_reviews[:3]:
        timeline_activities.append({
            'type': 'review',
            'date': review['date'].strftime('%b %d, %Y'),
            'raw_date': review['date'],
            'customer_name': review['customer_name'],
            'rating': review['rating'],
            'comment': review['comment']
        })
    
    # Add recent notifications
    from models.notifications import Notification
    recent_notifications = Notification.query.filter_by(user_id=user_id).order_by(Notification.created_at.desc()).limit(5).all()
    for entry in recent_notifications:
        timeline_activities.append({
            'type': 'notification',
            'date': entry.created_at.strftime('%b %d, %Y'),
            'raw_date': entry.created_at,
            'title': entry.title,
            'message': entry.message,
            'is_read': entry.is_read
        })
    
    # Sort timeline by raw_date descending
    timeline_activities.sort(key=lambda x: x.get('raw_date', datetime.now()), reverse=True)
    
    week_end = today + timedelta(days=7)
    
    upcoming_bookings = db.session.query(Booking, CustomerProfile, User).join(
        CustomerProfile, Booking.customer_id == CustomerProfile.customer_id
    ).join(
        User, CustomerProfile.user_id == User.user_id
    ).filter(
        Booking.companion_id == companion.companion_id,
        Booking.status.in_([BookingStatusEnum.APPROVED, BookingStatusEnum.PAID]),
        Booking.start_time >= today,
        Booking.start_time <= week_end
    ).order_by(Booking.start_time).all()
    
    formatted_upcoming = []
    for booking, customer, user in upcoming_bookings:
        duration_hours = (booking.end_time - booking.start_time).total_seconds() / 3600
        formatted_upcoming.append({
            'customer_name': customer.full_name or 'Anonymous',
            'start_time': booking.start_time,
            'duration': duration_hours,
            'location': booking.meeting_location or 'Not specified',
            'amount': float(booking.total_price)
        })
    
    # Prepare companion data
    companion_data = {
        'companion_id': companion.companion_id,
        'display_name': companion.display_name,
        'email': companion.user.email if companion.user else 'companion@email.com',
        'phone': '+1 (555) 987-6543',  # Placeholder - add to model if needed
        'age': companion.age,
        'gender': companion.gender.value,
        'date_of_birth': companion.date_of_birth.strftime('%Y-%m-%d') if companion.date_of_birth else '',
        'bio': companion.bio or '',
        'rate_per_hour': float(companion.rate_per_hour),
        'location': companion.location or '',
        'city': city,
        'state': state,
        'languages': languages,
        'personality_traits': personality_traits,
        'avg_rating': float(companion.avg_rating) if companion.avg_rating else 0,
        'verification_status': companion.verification_status.value,
        'photo_url': photo_url,
        'cover_photo_url': companion.cover_photo_url,
        'member_since': companion.user.created_at.year if companion.user and companion.user.created_at else 2022
    }
    
    # Get all photos for gallery management
    photos = db.session.query(CompanionPhoto).filter_by(
        companion_id=companion.companion_id
    ).order_by(CompanionPhoto.is_primary.desc()).all()
    
    formatted_photos = []
    for p in photos:
        p_url = p.photo_url
        p_photo_url = f"/static/{p_url}" if not p_url.startswith(('/', 'http')) else p_url
        formatted_photos.append({
            'photo_id': p.photo_id,
            'photo_url': p_photo_url,
            'is_primary': p.is_primary
        })

    return render_template('front/pages/dashboard-companion.html',
        companion=companion_data,
        photos=formatted_photos,
        pending_requests=formatted_requests,
        pending_count=len(formatted_requests),
        confirmed_bookings=formatted_bookings,
        total_earnings=float(total_earnings),
        monthly_earnings=float(monthly_earnings),
        total_bookings=total_bookings,
        monthly_bookings=monthly_bookings,
        reviews=formatted_reviews,
        total_reviews=total_reviews,
        response_rate=response_rate,
        acceptance_rate=acceptance_rate,
        completion_rate=completion_rate,
        upcoming_bookings=formatted_upcoming,
        availability_week=get_availability_week(companion.companion_id),
        awaiting_reports=awaiting_info_reports,
        timeline_activities=timeline_activities
    )

@app.post('/update-availability')
def update_availability():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    companion = db.session.query(CompanionProfile).filter_by(user_id=user_id).first()
    if not companion:
        flash('Companion profile not found', 'danger')
        return redirect(url_for('dashboard_companion'))
    
    try:
        # Clear existing availability
        Availability.query.filter_by(companion_id=companion.companion_id).delete()
        
        day_maps = {
            'MON': DayOfWeekEnum.MON,
            'TUE': DayOfWeekEnum.TUE,
            'WED': DayOfWeekEnum.WED,
            'THU': DayOfWeekEnum.THU,
            'FRI': DayOfWeekEnum.FRI,
            'SAT': DayOfWeekEnum.SAT,
            'SUN': DayOfWeekEnum.SUN
        }
        
        for prefix, day_enum in day_maps.items():
            if request.form.get(f'{prefix}_enabled') == 'on':
                start_str = request.form.get(f'{prefix}_start')
                end_str = request.form.get(f'{prefix}_end')
                
                if start_str and end_str:
                    new_avail = Availability(
                        companion_id=companion.companion_id,
                        day_of_week=day_enum,
                        start_time=datetime.strptime(start_str, '%H:%M').time(),
                        end_time=datetime.strptime(end_str, '%H:%M').time()
                    )
                    db.session.add(new_avail)
        
        db.session.commit()
        flash('Availability updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating availability: {str(e)}', 'danger')
        
    return redirect(url_for('dashboard_companion', _anchor='schedule'))

@app.get('/dashboard-admin')
def dashboard_admin():
    return render_template('front/pages/dashboard-admin.html')

@app.post('/update-profile-customer')
def update_profile_customer():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    customer = db.session.query(CustomerProfile).filter_by(user_id=user_id).first()
    if not customer:
        flash('Customer profile not found', 'danger')
        return redirect(url_for('dashboard_customer'))
    
    user = db.session.query(User).filter_by(user_id=user_id).first()
    
    try:
        # Update User basic info
        user.email = request.form.get('email')
        user.phone = request.form.get('phone')
        
        # Update Customer Profile
        customer.full_name = request.form.get('full_name')
        customer.location = request.form.get('location')
        customer.bio = request.form.get('bio')

        # Handle Photo Upload
        upload_folder = os.path.join('static', 'uploads', 'customer_photos')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        if 'profile_photo' in request.files:
            file = request.files['profile_photo']
            if file and file.filename:
                filename = secure_filename(f"{uuid.uuid4().hex}_{file.filename}")
                file_path = os.path.join(upload_folder, filename)
                file.save(file_path)
                customer.profile_photo = f"/static/uploads/customer_photos/{filename}"

        if 'cover_photo' in request.files:
            file = request.files['cover_photo']
            if file and file.filename:
                filename = secure_filename(f"cover_{uuid.uuid4().hex}_{file.filename}")
                file_path = os.path.join(upload_folder, filename)
                file.save(file_path)
                customer.cover_photo = f"/static/uploads/customer_photos/{filename}"
        
        dob_str = request.form.get('date_of_birth')
        if dob_str:
            customer.date_of_birth = datetime.strptime(dob_str, '%Y-%m-%d').date()
            
        gender_val = request.form.get('gender')
        if gender_val:
            customer.gender = GenderEnum[gender_val]
            
        db.session.commit()
        flash('Profile updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating profile: {str(e)}', 'danger')
        
    return redirect(url_for('dashboard_customer', _anchor='settings'))

@app.post('/update-profile-companion')
def update_profile_companion():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    print(f"DEBUG: update_profile_companion called for user_id {user_id}")
    print(f"DEBUG: Files received: {request.files}")
    print(f"DEBUG: Form data keys: {request.form.keys()}")

    companion = db.session.query(CompanionProfile).filter_by(user_id=user_id).first()
    if not companion:
        flash('Companion profile not found', 'danger')
        return redirect(url_for('dashboard_companion'))
    
    user = db.session.query(User).filter_by(user_id=user_id).first()
    
    try:
        # Update User basic info
        user.email = request.form.get('email')
        user.phone = request.form.get('phone')
        
        # Update Companion Profile
        companion.display_name = request.form.get('display_name')
        companion.location = request.form.get('location')
        companion.bio = request.form.get('bio')
        companion.rate_per_hour = float(request.form.get('rate_per_hour', 0))
        companion.age = int(request.form.get('age', 0))
        
        # Handle Photo Uploads
        upload_folder = os.path.join('static', 'uploads', 'companion_photos')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        # 1. Profile Photo
        if 'profile_photo' in request.files:
            file = request.files['profile_photo']
            if file and file.filename:
                filename = secure_filename(f"{uuid.uuid4().hex}_{file.filename}")
                file_path = os.path.join(upload_folder, filename)
                file.save(file_path)
                
                # Update CompanionPhoto (main)
                # First, set all existing photos to non-primary
                CompanionPhoto.query.filter_by(companion_id=companion.companion_id).update({'is_primary': False})
                
                # Create or update primary photo
                photo_url = f"/static/uploads/companion_photos/{filename}"
                new_photo = CompanionPhoto(
                    companion_id=companion.companion_id,
                    photo_url=photo_url,
                    is_primary=True
                )
                db.session.add(new_photo)

        # 2. Cover Photo
        if 'cover_photo' in request.files:
            file = request.files['cover_photo']
            if file and file.filename:
                filename = secure_filename(f"{uuid.uuid4().hex}_{file.filename}")
                file_path = os.path.join(upload_folder, filename)
                file.save(file_path)
                
                companion.cover_photo_url = f"/static/uploads/companion_photos/{filename}"

        # Handle JSON fields (languages, personality_traits)
        languages = request.form.getlist('languages')
        custom_language = request.form.get('custom_language')
        if custom_language and custom_language.strip():
            languages.append(custom_language.strip())
            
        companion.languages = languages
            
        traits = request.form.getlist('personality_traits')
        custom_trait = request.form.get('custom_personality_trait')
        if custom_trait and custom_trait.strip():
            traits.append(custom_trait.strip())
            
        companion.personality_traits = traits
            
        db.session.commit()
        flash('Profile updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating profile: {str(e)}', 'danger')
        
    return redirect(url_for('dashboard_companion', _anchor='settings'))

@app.post('/upload-gallery-photo')
def upload_gallery_photo():
    from flask import jsonify
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Login required'}), 401
        
    companion = db.session.query(CompanionProfile).filter_by(user_id=user_id).first()
    if not companion:
        return jsonify({'success': False, 'message': 'Companion profile not found'}), 404
        
    if 'gallery_photos' not in request.files:
        return jsonify({'success': False, 'message': 'No files uploaded'}), 400
        
    files = request.files.getlist('gallery_photos')
    if not files or files[0].filename == '':
        return jsonify({'success': False, 'message': 'No files selected'}), 400
        
    # Check current count
    current_count = CompanionPhoto.query.filter_by(companion_id=companion.companion_id).count()
    if current_count + len(files) > 10:
        return jsonify({'success': False, 'message': f'Cannot exceed 10 photos. You can only add {max(0, 10 - current_count)} more.'}), 400
        
    upload_folder = os.path.join('static', 'uploads', 'companion_photos')
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
        
    allowed_ext = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
    uploaded_photos = []
    
    for file in files:
        if file and file.filename:
            # Use save_image from upload_service
            result = save_image(file, upload_folder, allowed_ext)
            
            if isinstance(result, str): # Error message
                # Skip this file but continue others
                continue
                
            # Create new CompanionPhoto record
            photo_url = f"uploads/companion_photos/{result['original']}"
            
            new_photo = CompanionPhoto(
                companion_id=companion.companion_id,
                photo_url=photo_url,
                is_primary=False
            )
            db.session.add(new_photo)
            db.session.commit()
            
            uploaded_photos.append({
                'photo_id': new_photo.photo_id,
                'photo_url': f"/static/{photo_url}",
                'is_primary': False
            })
            
    if not uploaded_photos:
        return jsonify({'success': False, 'message': 'Upload failed for all selected files. Ensure they are valid images (png, jpg, jpeg, webp, gif).'}), 400
    
    return jsonify({
        'success': True, 
        'message': f'{len(uploaded_photos)} photo(s) uploaded successfully',
        'photos': uploaded_photos
    })

@app.post('/set-primary-photo/<int:photo_id>')
def set_primary_photo(photo_id):
    from flask import jsonify
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Login required'}), 401
        
    companion = db.session.query(CompanionProfile).filter_by(user_id=user_id).first()
    if not companion:
        return jsonify({'success': False, 'message': 'Companion profile not found'}), 404
        
    # Verify photo belongs to companion
    photo = CompanionPhoto.query.filter_by(photo_id=photo_id, companion_id=companion.companion_id).first()
    if not photo:
        return jsonify({'success': False, 'message': 'Photo not found'}), 404
        
    # Reset all others
    CompanionPhoto.query.filter_by(companion_id=companion.companion_id).update({'is_primary': False})
    
    # Set this one as primary
    photo.is_primary = True
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Profile picture updated successfully'})

@app.post('/delete-gallery-photo/<int:photo_id>')
def delete_gallery_photo(photo_id):
    from flask import jsonify
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Login required'}), 401
        
    companion = db.session.query(CompanionProfile).filter_by(user_id=user_id).first()
    if not companion:
        return jsonify({'success': False, 'message': 'Companion profile not found'}), 404
        
    photo = CompanionPhoto.query.filter_by(photo_id=photo_id, companion_id=companion.companion_id).first()
    if not photo:
        return jsonify({'success': False, 'message': 'Photo not found'}), 404
        
    if photo.is_primary:
        return jsonify({'success': False, 'message': 'Cannot delete your primary profile photo. Please set another as primary first.'}), 400
        
    # Delete from disk
    try:
        # Resolve absolute path
        p_url = photo.photo_url
        if p_url.startswith('/static/'):
            p_url = p_url[len('/static/'):]
        
        file_path = os.path.join('static', p_url)
        if os.path.exists(file_path):
            os.remove(file_path)
            
        # Also remove resized and thumbnail if they exist
        dir_name = os.path.dirname(file_path)
        base_name = os.path.basename(file_path)
        name, ext = os.path.splitext(base_name)
        
        for prefix in ['resized_', 'thumb_']:
            extra_path = os.path.join(dir_name, f"{prefix}{name}{ext}")
            if os.path.exists(extra_path):
                os.remove(extra_path)
    except Exception as e:
        print(f"DEBUG: Error deleting physical file: {e}")
        
    db.session.delete(photo)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Photo removed from gallery'})
