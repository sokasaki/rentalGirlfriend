from app import app, render_template, db
from sqlalchemy import func
from flask import request, session, jsonify, redirect, url_for
from models.bookings import Booking, BookingStatusEnum
from models.customer_profiles import CustomerProfile
from models.companion_profiles import CompanionProfile, VerificationStatusEnum
from models.notifications import Notification
from models.payments import Payment, PaymentMethodEnum, PaymentStatusEnum
from models.availability import Availability, DayOfWeekEnum
from models.reviews import Review, ReviewStatusEnum
from datetime import datetime, timedelta
from decimal import Decimal
import stripe
import time
import requests

# Initialize Stripe
stripe.api_key = app.config['STRIPE_SECRET_KEY']


def _calculate_total_with_fee(booking):
    subtotal = float(booking.total_price)
    service_fee = subtotal * 0.1
    return subtotal + service_fee


def _parse_booking_datetime(date_str, time_str):
    if not date_str or not time_str:
        raise ValueError("Date and time are required")

    normalized_time = time_str.strip().upper()
    formats = [
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %I:%M %p",
        "%Y-%m-%d %I:%M:%S %p",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(f"{date_str} {normalized_time}", fmt)
        except ValueError:
            continue

    raise ValueError("Invalid date or time format")


def _weekday_to_enum(dt):
    day_map = {
        0: DayOfWeekEnum.MON,
        1: DayOfWeekEnum.TUE,
        2: DayOfWeekEnum.WED,
        3: DayOfWeekEnum.THU,
        4: DayOfWeekEnum.FRI,
        5: DayOfWeekEnum.SAT,
        6: DayOfWeekEnum.SUN,
    }
    return day_map[dt.weekday()]


def _is_within_availability(companion_id, start_dt, end_dt):
    if start_dt.date() != end_dt.date():
        print(f"DEBUG [AVAILABILITY] Outside range: Start date {start_dt.date()} != End date {end_dt.date()}")
        return False

    day_enum = _weekday_to_enum(start_dt)
    print(f"DEBUG [AVAILABILITY] Checking companion {companion_id} for {day_enum.value}")
    
    # Use value comparison for Enum if needed
    slots = Availability.query.filter_by(
        companion_id=companion_id
    ).all()
    
    # Filter by day in python to be safer with Enum types if query has issues
    matching_slots = [s for s in slots if s.day_of_week == day_enum or s.day_of_week.value == day_enum.value]

    print(f"DEBUG [AVAILABILITY] Found {len(matching_slots)} slots for {day_enum.value}")
    
    if not matching_slots:
        print(f"DEBUG [AVAILABILITY] Result: FAILED (No slots for {day_enum.value})")
        return False

    start_time = start_dt.time()
    end_time = end_dt.time()
    
    print(f"DEBUG [AVAILABILITY] Requested Time: {start_time} to {end_time}")

    for slot in matching_slots:
        print(f"DEBUG [AVAILABILITY] Checking Slot: {slot.start_time} to {slot.end_time}")
        # Check if BOTH start AND end times are within the slot
        if slot.start_time <= start_time and slot.end_time >= end_time:
            print(f"DEBUG [AVAILABILITY] Result: PASSED (Match found in slot {slot.availability_id})")
            return True
    
    print(f"DEBUG [AVAILABILITY] Result: FAILED (No slot covers the requested internal {start_time}-{end_time})")
    return False



@app.post('/create_booking')
def create_booking():
    # Check if user is logged in
    if 'user_id' not in session:
        print("DEBUG: User not logged in")
        return jsonify({
            'success': False,
            'message': 'Please login to make a booking',
            'redirect': url_for('login')
        }), 401
    
    try:
        # Get customer profile from session
        customer = CustomerProfile.query.filter_by(user_id=session['user_id']).first()
        if not customer:
            print(f"DEBUG: Customer profile not found for user {session['user_id']}")
            return jsonify({
                'success': False,
                'message': 'Customer profile not found. Please complete your registration.'
            }), 404
        
        print(f"DEBUG: Processing booking for customer {customer.customer_id}")
        
        # Get form data
        data = request.get_json() if request.is_json else request.form
        print(f"DEBUG: Request data: {data}")
        
        try:
            companion_id = int(data.get('companion_id'))
            date_str = data.get('date')
            time_str = data.get('time')
            duration = int(data.get('duration'))
            location = data.get('location')
            notes = data.get('notes', '')
        except (ValueError, TypeError) as e:
            print(f"DEBUG: Error parsing form fields: {e}")
            return jsonify({
                'success': False,
                'message': f'Invalid form data: {str(e)}'
            }), 400
        
        if duration <= 0:
            print(f"DEBUG: Invalid duration: {duration}")
            return jsonify({
                'success': False,
                'message': 'Duration must be greater than 0'
            }), 400

        # Validate companion exists
        companion = CompanionProfile.query.get(companion_id)
        if not companion:
            print(f"DEBUG: Companion {companion_id} not found")
            return jsonify({
                'success': False,
                'message': 'Companion not found'
            }), 404

        if companion.verification_status != VerificationStatusEnum.APPROVED:
            print(f"DEBUG: Companion {companion_id} not approved. Status: {companion.verification_status}")
            return jsonify({
                'success': False,
                'message': 'This companion is not currently available for booking'
            }), 400
        
        # Parse datetime
        print(f"DEBUG: Parsing date {date_str} and time {time_str}")
        booking_datetime = _parse_booking_datetime(date_str, time_str)
        start_time = booking_datetime
        end_time = booking_datetime + timedelta(hours=duration)

        print(f"DEBUG: Start time: {start_time} (date: {start_time.date()})")
        print(f"DEBUG: End time: {end_time} (date: {end_time.date()})")
        print(f"DEBUG: Same day? {start_time.date() == end_time.date()}")

        if start_time.date() != end_time.date():
            return jsonify({
                'success': False,
                'message': 'Booking must start and end on the same day'
            }), 400
        
        # Check if booking is in the future
        if start_time <= datetime.now():
            print(f"DEBUG: Booking in past. Start: {start_time}, Now: {datetime.now()}")
            return jsonify({
                'success': False,
                'message': 'Booking time must be in the future'
            }), 400

        # Validate booking fits companion availability
        availability_check = _is_within_availability(companion_id, start_time, end_time)
        print(f"DEBUG: Availability check result: {availability_check}")
        print(f"DEBUG: Companion {companion_id}, Start: {start_time.time()}, End: {end_time.time()}")
        
        if not availability_check:
            print(f"DEBUG: Availability check FAILED for companion {companion_id}")
            return jsonify({
                'success': False,
                'message': 'Selected date/time is outside companion availability'
            }), 400

        # Prevent overlapping bookings for same companion
        overlapping_booking = Booking.query.filter(
            Booking.companion_id == companion_id,
            Booking.status.in_([
                BookingStatusEnum.PENDING,
                BookingStatusEnum.APPROVED,
                BookingStatusEnum.PAID,
                BookingStatusEnum.COMPLETED
            ]),
            Booking.start_time < end_time,
            Booking.end_time > start_time
        ).first()

        if overlapping_booking:
            return jsonify({
                'success': False,
                'message': 'This time slot is no longer available. Please choose another time.'
            }), 409
        
        # Calculate total price
        total_price = Decimal(str(companion.rate_per_hour)) * Decimal(str(duration))
        
        # Create booking
        new_booking = Booking(
            customer_id=customer.customer_id,
            companion_id=companion_id,
            start_time=start_time,
            end_time=end_time,
            status=BookingStatusEnum.PENDING,
            total_price=total_price,
            meeting_location=location
        )
        
        db.session.add(new_booking)
        db.session.commit()
        
        print(f"DEBUG: Booking created successfully - ID: {new_booking.booking_id}")
        
        # Format booking details for response
        booking_date = start_time.strftime('%A, %B %d, %Y')
        booking_time = start_time.strftime('%H:%M')
        duration_text = f'{duration} hour' if duration == 1 else f'{duration} hours'
        
        return jsonify({
            'success': True,
            'message': f'Booking request sent successfully! Waiting for companion approval.',
            'booking_id': new_booking.booking_id,
            'booking_details': {
                'companion_name': companion.display_name,
                'date': booking_date,
                'time': booking_time,
                'duration': duration_text,
                'location': location,
                'total_price': float(total_price)
            }
        }), 201
        
    except ValueError as e:
        print(f"DEBUG: ValueError - {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e) or 'Invalid date or time format'
        }), 400
    except Exception as e:
        print(f"DEBUG: Exception - {str(e)}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }), 500

@app.post('/approve_booking/<int:booking_id>')
def approve_booking(booking_id):
    # Check if user is logged in
    if 'user_id' not in session:
        return jsonify({
            'success': False,
            'message': 'Please login first',
            'redirect': url_for('login')
        }), 401
    
    try:
        # Get companion profile from session
        companion = CompanionProfile.query.filter_by(user_id=session['user_id']).first()
        if not companion:
            return jsonify({
                'success': False,
                'message': 'Companion profile not found'
            }), 404
        
        # Get booking and verify it belongs to this companion
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({
                'success': False,
                'message': 'Booking not found'
            }), 404
        
        if booking.companion_id != companion.companion_id:
            return jsonify({
                'success': False,
                'message': 'Unauthorized to approve this booking'
            }), 403
        
        if booking.status != BookingStatusEnum.PENDING:
            return jsonify({
                'success': False,
                'message': f'Booking cannot be approved. Current status: {booking.status.value}'
            }), 400
        
        # Approve booking
        booking.status = BookingStatusEnum.APPROVED
        
        # Create notification for customer
        customer = CustomerProfile.query.get(booking.customer_id)
        notification = Notification(
            user_id=customer.user_id,
            title="Booking Approved!",
            message=f"Your booking with {companion.display_name} has been approved. You can now proceed with payment."
        )
        db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Booking approved successfully! Customer can now proceed with payment.'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }), 500

@app.post('/reject_booking/<int:booking_id>')
def reject_booking(booking_id):
    # Check if user is logged in
    if 'user_id' not in session:
        return jsonify({
            'success': False,
            'message': 'Please login first',
            'redirect': url_for('login')
        }), 401
    
    try:
        # Get companion profile from session
        companion = CompanionProfile.query.filter_by(user_id=session['user_id']).first()
        if not companion:
            return jsonify({
                'success': False,
                'message': 'Companion profile not found'
            }), 404
        
        # Get booking and verify it belongs to this companion
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({
                'success': False,
                'message': 'Booking not found'
            }), 404
        
        if booking.companion_id != companion.companion_id:
            return jsonify({
                'success': False,
                'message': 'Unauthorized to reject this booking'
            }), 403
        
        if booking.status != BookingStatusEnum.PENDING:
            return jsonify({
                'success': False,
                'message': f'Booking cannot be rejected. Current status: {booking.status.value}'
            }), 400
        
        # Get rejection reason from request
        data = request.get_json() if request.is_json else request.form
        rejection_reason = data.get('rejection_reason', 'No reason provided')
        
        # Reject booking
        booking.status = BookingStatusEnum.REJECTED
        booking.rejection_reason = rejection_reason
        
        # Create notification for customer
        customer = CustomerProfile.query.get(booking.customer_id)
        notification = Notification(
            user_id=customer.user_id,
            title="Booking Declined",
            message=f"Your booking with {companion.display_name} was declined. Reason: {rejection_reason}"
        )
        db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Booking rejected successfully.'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }), 500

@app.get('/payment/<int:booking_id>')
def payment(booking_id):
    # Check if user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get customer profile
    customer = CustomerProfile.query.filter_by(user_id=session['user_id']).first()
    if not customer:
        return redirect(url_for('register_customer'))
    
    # Get booking with companion details
    booking = Booking.query.get(booking_id)
    if not booking:
        return "Booking not found", 404
    
    if booking.customer_id != customer.customer_id:
        return "Unauthorized", 403
    
    # Check if booking is approved
    if booking.status != BookingStatusEnum.APPROVED:
        return f"Payment not available. Booking status: {booking.status.value}. Please wait for companion approval.", 400
    
    # Get companion details
    companion = CompanionProfile.query.get(booking.companion_id)
    if not companion:
        return "Companion not found", 404
    
    # Attach companion to booking for template
    booking.companion = companion

    
    # Pass Stripe public key to template
    return render_template(
        'front/pages/payment.html', 
        booking=booking,
        stripe_public_key=app.config['STRIPE_PUBLIC_KEY']
    )

@app.post('/create-payment-intent')
def create_payment_intent():
    # Check if user is logged in
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        booking_id = data.get('booking_id')
        
        # Get booking
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404
        
        # Verify user owns this booking
        customer = CustomerProfile.query.filter_by(user_id=session['user_id']).first()
        if not customer or booking.customer_id != customer.customer_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Verify booking is approved
        if booking.status != BookingStatusEnum.APPROVED:
            return jsonify({'error': 'Booking must be approved before payment'}), 400
        
        # Calculate total with service fee
        subtotal = float(booking.total_price)
        service_fee = subtotal * 0.1
        total = subtotal + service_fee
        
        # Create payment intent (Stripe uses cents)
        intent = stripe.PaymentIntent.create(
            amount=int(total * 100),  # Convert to cents
            currency='usd',
            metadata={
                'booking_id': booking.booking_id,
                'customer_id': customer.customer_id
            }
        )
        
        return jsonify({
            'clientSecret': intent.client_secret
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.post('/payment-success')
def payment_success():
    # Check if user is logged in
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        booking_id = data.get('booking_id')
        payment_intent_id = data.get('payment_intent_id')
        
        # Get booking
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404
        
        # Verify user owns this booking
        customer = CustomerProfile.query.filter_by(user_id=session['user_id']).first()
        if not customer or booking.customer_id != customer.customer_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Update booking status to PAID
        booking.status = BookingStatusEnum.PAID
        
        # Create payment record
        subtotal = float(booking.total_price)
        service_fee = subtotal * 0.1
        total = subtotal + service_fee
        
        payment = Payment(
            booking_id=booking.booking_id,
            amount=Decimal(str(total)),
            method=PaymentMethodEnum.CARD,
            status=PaymentStatusEnum.PAID,
            paid_at=datetime.now()
        )
        
        db.session.add(payment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Payment successful!',
            'redirect': url_for('receipt', payment_id=payment.payment_id)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.get('/get_companion_availability/<int:companion_id>')
def get_companion_availability(companion_id):
    """Get available days, time slots, and existing bookings for a companion"""
    try:
        companion = CompanionProfile.query.get(companion_id)
        if not companion:
            return jsonify({'success': False, 'message': 'Companion not found'}), 404
        
        # Get all availability slots for this companion
        slots = Availability.query.filter_by(companion_id=companion_id).all()
        
        # Group by day of week
        available_days = {}
        for slot in slots:
            day = slot.day_of_week.value
            if day not in available_days:
                available_days[day] = []
            available_days[day].append({
                'start_time': slot.start_time.strftime('%H:%M'),
                'end_time': slot.end_time.strftime('%H:%M')
            })
        
        # Get existing bookings to avoid overlaps (next 30 days)
        from models.bookings import Booking, BookingStatusEnum
        today = datetime.now().date()
        future_limit = today + timedelta(days=30)
        
        bookings = Booking.query.filter(
            Booking.companion_id == companion_id,
            Booking.status.in_([
                BookingStatusEnum.PENDING,
                BookingStatusEnum.APPROVED,
                BookingStatusEnum.PAID,
                BookingStatusEnum.COMPLETED
            ]),
            Booking.start_time >= datetime.combine(today, datetime.min.time()),
            Booking.start_time <= datetime.combine(future_limit, datetime.max.time())
        ).all()
        
        booked_slots = []
        for b in bookings:
            booked_slots.append({
                'date': b.start_time.strftime('%Y-%m-%d'),
                'start': b.start_time.strftime('%H:%M'),
                'end': b.end_time.strftime('%H:%M')
            })
        
        # Convert day names to weekday numbers (0=Mon, 1=Tue, etc.)
        day_to_weekday = {
            'MON': 0, 'TUE': 1, 'WED': 2, 'THU': 3,
            'FRI': 4, 'SAT': 5, 'SUN': 6
        }
        
        return jsonify({
            'success': True,
            'available_days': available_days,
            'booked_slots': booked_slots,
            'day_to_weekday': day_to_weekday
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.get('/confirmation')
def confirmation():
    return render_template('front/pages/confirmation.html')
@app.get('/get_booking_details/<int:booking_id>')
def get_booking_details(booking_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    current_user_id = session['user_id']
    booking = Booking.query.get(booking_id)
    
    if not booking:
        return jsonify({'success': False, 'message': 'Booking not found'}), 404
        
    # Security check: Only the involved companion or customer can view details
    companion = CompanionProfile.query.filter_by(companion_id=booking.companion_id).first()
    customer = CustomerProfile.query.filter_by(customer_id=booking.customer_id).first()
    
    if companion.user_id != current_user_id and customer.user_id != current_user_id:
        return jsonify({'success': False, 'message': 'Forbidden'}), 403
        
    # Prepare response data
    duration_hours = (booking.end_time - booking.start_time).total_seconds() / 3600
    
    # Get payment info if exists
    payment = Payment.query.filter_by(booking_id=booking.booking_id).first()
    payment_status = payment.status.value if payment else 'UNPAID'
    
    data = {
        'success': True,
        'booking': {
            'id': booking.booking_id,
            'start_time': booking.start_time.strftime('%b %d, %Y at %H:%M'),
            'duration': f"{duration_hours:.0f}h",
            'location': booking.meeting_location,
            'total_price': float(booking.total_price),
            'status': booking.status.value,
            'rejection_reason': booking.rejection_reason
        },
        'customer': {
            'name': customer.full_name,
            'photo': customer.profile_photo or url_for('static', filename='img/default-avatar.png'),
            'location': customer.location,
            'bio': customer.bio or 'No bio provided.'
        },
        'payment': {
            'status': payment_status
        }
    }
    
    return jsonify(data)


@app.post('/complete_booking/<int:booking_id>')
def complete_booking(booking_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({'success': False, 'message': 'Booking not found'}), 404
    
    # Check if user is the customer of this booking
    customer = CustomerProfile.query.filter_by(customer_id=booking.customer_id).first()
    if not customer or customer.user_id != session['user_id']:
        return jsonify({'success': False, 'message': 'Forbidden'}), 403
    
    # Check if end_time has passed
    if booking.end_time > datetime.now():
        return jsonify({'success': False, 'message': 'Session has not ended yet'}), 400
    
    if booking.status == BookingStatusEnum.COMPLETED:
        return jsonify({'success': False, 'message': 'Booking already completed'}), 400
        
    booking.status = BookingStatusEnum.COMPLETED
    db.session.commit()
    
    # Create notification for companion
    comp_notif = Notification(
        user_id=CompanionProfile.query.get(booking.companion_id).user_id,
        title="Session Completed",
        message=f"Your session with {customer.full_name} has been marked as completed. You can expect a review soon!",
        created_at=datetime.utcnow()
    )
    db.session.add(comp_notif)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Booking marked as completed'})


@app.post('/submit_review/<int:booking_id>')
def submit_review(booking_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({'success': False, 'message': 'Booking not found'}), 404
        
    if booking.status != BookingStatusEnum.COMPLETED:
        return jsonify({'success': False, 'message': 'Booking must be completed before reviewing'}), 400
        
    # Check if already reviewed
    existing_review = Review.query.filter_by(booking_id=booking_id).first()
    if existing_review:
        return jsonify({'success': False, 'message': 'You have already reviewed this booking'}), 400
        
    data = request.get_json()
    rating = data.get('rating')
    comment = data.get('comment')
    
    if not rating or not (1 <= int(rating) <= 5):
        return jsonify({'success': False, 'message': 'Invalid rating'}), 400
        
    # Create review
    review = Review(
        booking_id=booking_id,
        rating=int(rating),
        comment=comment,
        created_at=datetime.utcnow()
    )
    db.session.add(review)
    db.session.flush()  # Ensure review is available for calculation
    
    # Update companion average rating using the model helper
    companion = CompanionProfile.query.get(booking.companion_id)
    companion.update_avg_rating()
    
    # Notification for companion
    customer = CustomerProfile.query.filter_by(customer_id=booking.customer_id).first()
    notif = Notification(
        user_id=companion.user_id,
        title="New Review!",
        message=f"You received a {rating}-star review from {customer.full_name if customer else 'a client'}!",
        created_at=datetime.utcnow()
    )
    db.session.add(notif)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Review submitted successfully'})


@app.post('/submit_review_reply/<int:review_id>')
def submit_review_reply(review_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    review = Review.query.get(review_id)
    if not review:
        return jsonify({'success': False, 'message': 'Review not found'}), 404
        
    booking = Booking.query.get(review.booking_id)
    companion = CompanionProfile.query.filter_by(user_id=session['user_id']).first()
    
    if not companion or booking.companion_id != companion.companion_id:
        return jsonify({'success': False, 'message': 'Forbidden'}), 403
        
    data = request.get_json()
    reply_content = data.get('reply')
    
    if not reply_content:
        return jsonify({'success': False, 'message': 'Reply content is required'}), 400
        
    review.reply = reply_content
    review.replied_at = datetime.utcnow()
    
    # Notification for customer
    customer = CustomerProfile.query.get(booking.customer_id)
    notif = Notification(
        user_id=customer.user_id,
        title="New Reply to Your Review",
        message=f"{companion.display_name} replied to your review!",
        created_at=datetime.utcnow()
    )
    db.session.add(notif)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Reply submitted successfully'})

