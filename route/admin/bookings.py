from app import app, render_template, request, db, flash, redirect, url_for, admin_required, permission_required
from models.bookings import Booking, BookingStatusEnum
from models.customer_profiles import CustomerProfile
from models.companion_profiles import CompanionProfile

@app.get('/admin/bookings')
@admin_required
@permission_required('booking:view')
def bookings():
    # Get query parameters for search and filter
    search_query = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '')
    
    # Build query (newest first)
    query = Booking.query.order_by(Booking.booking_id.desc())
    
    # Apply status filter
    # Map template status values to actual enum values
    status_enum_map = {
        'PENDING': [BookingStatusEnum.PENDING],
        'CONFIRMED': [BookingStatusEnum.APPROVED, BookingStatusEnum.PAID],
        'COMPLETED': [BookingStatusEnum.COMPLETED],
        'CANCELLED': [BookingStatusEnum.REJECTED],
    }
    
    if status_filter and status_filter in status_enum_map:
        query = query.filter(Booking.status.in_(status_enum_map[status_filter]))
    
    # Apply search filter (by customer name or companion name)
    if search_query:
        query = query.join(
            CustomerProfile, Booking.customer_id == CustomerProfile.customer_id
        ).join(
            CompanionProfile, Booking.companion_id == CompanionProfile.companion_id
        ).filter(
            (CustomerProfile.full_name.ilike(f'%{search_query}%')) |
            (CompanionProfile.display_name.ilike(f'%{search_query}%'))
        )
    
    # Fetch filtered bookings
    all_bookings = query.all()
    
    # Calculate statistics (from ALL bookings, not filtered)
    all_bookings_for_stats = Booking.query.all()
    total_bookings = len(all_bookings_for_stats)
    pending_bookings_count = len([b for b in all_bookings_for_stats if b.status == BookingStatusEnum.PENDING])
    confirmed_bookings_count = len([b for b in all_bookings_for_stats if b.status == BookingStatusEnum.APPROVED])
    completed_bookings_count = len([b for b in all_bookings_for_stats if b.status == BookingStatusEnum.COMPLETED])
    
    # Format booking data for template
    bookings_data = []
    for booking in all_bookings:
        customer = booking.customer
        companion = booking.companion
        
        # Get companion's primary photo
        companion_photo = None
        if companion and companion.photos:
            primary = [p for p in companion.photos if p.is_primary]
            companion_photo = primary[0].photo_url if primary else (companion.photos[0].photo_url if companion.photos else None)
        
        # Map status to template format
        status_map = {
            BookingStatusEnum.PENDING: 'PENDING',
            BookingStatusEnum.APPROVED: 'CONFIRMED',
            BookingStatusEnum.REJECTED: 'CANCELLED',
            BookingStatusEnum.PAID: 'CONFIRMED',
            BookingStatusEnum.COMPLETED: 'COMPLETED'
        }
        
        bookings_data.append({
            'booking_id': f'#BC-{booking.booking_id}',
            'id': booking.booking_id,
            'customer_name': customer.full_name if customer else 'N/A',
            'customer_avatar': customer.profile_photo if customer else None,
            'companion_name': companion.display_name if companion else 'N/A',
            'companion_avatar': companion_photo,
            'booking_date': booking.start_time,
            'booking_time': booking.start_time.strftime('%I:%M %p') if booking.start_time else 'TBD',
            'duration': f"{(booking.end_time - booking.start_time).total_seconds() / 3600:.0f} hours" if booking.end_time and booking.start_time else 'N/A',
            'amount': float(booking.total_price or 0),
            'status': status_map.get(booking.status, 'PENDING')
        })
    
    # Get pending count for sidebar badge
    from models import CompanionProfile as CP
    pending_count = CP.query.filter_by(verification_status='PENDING').count()
    
    return render_template(
        'admin/bookings.html',
        active_page='bookings',
        total_bookings=total_bookings,
        pending_bookings_count=pending_bookings_count,
        confirmed_bookings_count=confirmed_bookings_count,
        completed_bookings_count=completed_bookings_count,
        bookings=bookings_data,
        pending_count=pending_count,
        search_query=search_query,
        status_filter=status_filter
    )

@app.get('/admin/bookings/view/<int:booking_id>')
@admin_required
@permission_required('booking:view')
def view_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    # Get associated payment and review
    from models import Payment, Review
    payment = Payment.query.filter_by(booking_id=booking.booking_id).first()
    review = Review.query.filter_by(booking_id=booking.booking_id).first()
    
    # Get pending count for sidebar
    from models import CompanionProfile as CP
    pending_count = CP.query.filter_by(verification_status='PENDING').count()
    
    return render_template(
        'admin/booking/view_detail.html',
        active_page='bookings',
        booking=booking,
        payment=payment,
        review=review,
        pending_count=pending_count
    )

@app.post('/admin/bookings/cancel/<int:booking_id>')
@admin_required
@permission_required('booking:manage')
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    booking.status = BookingStatusEnum.REJECTED
    db.session.commit()
    flash(f'Booking #{booking_id} has been cancelled.', 'success')
    return redirect(url_for('bookings'))

@app.post('/admin/bookings/delete/<int:booking_id>')
@admin_required
@permission_required('booking:manage')
def delete_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    db.session.delete(booking)
    db.session.commit()
    flash(f'Booking #{booking_id} has been deleted.', 'success')
    return redirect(url_for('bookings'))