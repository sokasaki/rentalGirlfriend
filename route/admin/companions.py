from app import app, render_template, request, admin_required, permission_required
from sqlalchemy import func
from models.companion_profiles import CompanionProfile, VerificationStatusEnum
from models.bookings import Booking, BookingStatusEnum
from models.users import User

@app.get('/admin/companions')
@admin_required
@permission_required('companion:view')
def companions():  # Admin dashboard home
    # Get query parameters for search and filter
    search_query = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '')
    sort_by = request.args.get('sort', 'newest')
    
    # Get pending companions
    pending_companions = CompanionProfile.query.filter_by(
        verification_status=VerificationStatusEnum.PENDING
    ).join(User).all()
    
    # Build query for approved companions
    query = CompanionProfile.query.filter_by(
        verification_status=VerificationStatusEnum.APPROVED
    ).join(User)
    
    # Apply search filter (name or email)
    if search_query:
        query = query.filter(
            (CompanionProfile.display_name.ilike(f'%{search_query}%')) |
            (User.email.ilike(f'%{search_query}%'))
        )
    
    # Apply status filter (verification status)
    if status_filter:
        query = CompanionProfile.query.join(User)
        if search_query:
            query = query.filter(
                (CompanionProfile.display_name.ilike(f'%{search_query}%')) |
                (User.email.ilike(f'%{search_query}%'))
            )
        query = query.filter(CompanionProfile.verification_status == status_filter)
    
    approved_companions = query.all()
    
    # Calculate booking counts and revenue for each companion
    companion_stats = []
    for companion in approved_companions:
        bookings = Booking.query.filter_by(companion_id=companion.companion_id).all()
        booking_count = len(bookings)
        
        # Calculate total revenue from paid/completed bookings
        total_revenue = sum([
            float(b.total_price) for b in bookings 
            if b.status in [BookingStatusEnum.PAID, BookingStatusEnum.COMPLETED]
        ])
        
        companion_stats.append({
            'companion': companion,
            'user': companion.user,
            'booking_count': booking_count,
            'total_revenue': total_revenue
        })
    
    # Apply sorting
    if sort_by == 'rating':
        companion_stats.sort(key=lambda x: float(x['companion'].avg_rating or 0), reverse=True)
    elif sort_by == 'bookings':
        companion_stats.sort(key=lambda x: x['booking_count'], reverse=True)
    else:  # newest
        companion_stats.sort(key=lambda x: x['user'].created_at or '', reverse=True)
    
    return render_template(
        'admin/companions.html', 
        active_page='companions',
        pending_companions=pending_companions,
        companion_stats=companion_stats,
        pending_count=len(pending_companions),
        search_query=search_query,
        status_filter=status_filter,
        sort_by=sort_by
    )

@app.get('/admin/companions/view/<int:id>')
@admin_required
@permission_required('companion:view')
def view_companion(id):
    """Review page for PENDING companion applications (approval form)"""
    from models import CompanionProfile, User, CompanionPhoto, Availability, Booking, Review
    
    # Get companion with user details
    companion = CompanionProfile.query.filter_by(companion_id=id).first()
    if not companion:
        from flask import flash, redirect, url_for
        flash('Companion not found', 'error')
        return redirect(url_for('companions'))
    
    # Get photos
    photos = CompanionPhoto.query.filter_by(companion_id=id).all()
    
    # Get availability
    availability = Availability.query.filter_by(companion_id=id).all()
    
    # Get bookings with reviews
    bookings = Booking.query.filter_by(companion_id=id).all()
    reviews = Review.query.join(Booking).filter(Booking.companion_id == id).all()
    
    # Get pending count for sidebar
    pending_count = CompanionProfile.query.filter_by(verification_status='PENDING').count()
    
    return render_template(
        'admin/companion/view.html',
        active_page='companions',
        companion=companion,
        user=companion.user,
        photos=photos,
        availability=availability,
        bookings=bookings,
        reviews=reviews,
        pending_count=pending_count
    )

@app.get('/admin/companions/view_detail/<int:id>')
@admin_required
@permission_required('companion:view')
def view_companion_detail(id):
    """Detail view page for APPROVED/REJECTED companions (read-only)"""
    from models import CompanionProfile, User, CompanionPhoto, Availability, Booking, Review
    
    # Get companion with user details
    companion = CompanionProfile.query.filter_by(companion_id=id).first()
    if not companion:
        from flask import flash, redirect, url_for
        flash('Companion not found', 'error')
        return redirect(url_for('companions'))
    
    # Get photos
    photos = CompanionPhoto.query.filter_by(companion_id=id).all()
    
    # Get availability
    availability = Availability.query.filter_by(companion_id=id).all()
    
    # Get bookings with reviews
    bookings = Booking.query.filter_by(companion_id=id).all()
    reviews = Review.query.join(Booking).filter(Booking.companion_id == id).all()
    
    # Get pending count for sidebar
    pending_count = CompanionProfile.query.filter_by(verification_status='PENDING').count()
    
    return render_template(
        'admin/companion/view_detail.html',
        active_page='companions',
        companion=companion,
        user=companion.user,
        photos=photos,
        availability=availability,
        bookings=bookings,
        reviews=reviews,
        pending_count=pending_count
    )

@app.post('/admin/companions/approve/<int:id>')
@admin_required
@permission_required('companion:verify')
def approve_companion(id):
    from models import CompanionProfile, Notification
    from flask import flash, redirect, url_for
    from extensions import db
    
    companion = CompanionProfile.query.filter_by(companion_id=id).first()
    if not companion:
        flash('Companion not found', 'error')
        return redirect(url_for('companions'))
    
    # Update verification status
    companion.verification_status = VerificationStatusEnum.APPROVED
    
    # Create notification for companion
    notification = Notification(
        user_id=companion.user_id,
        title='Application Approved',
        message=f'Congratulations! Your companion application has been approved. You can now start receiving bookings.',
        is_read=False
    )
    db.session.add(notification)
    db.session.commit()
    
    flash(f'{companion.display_name} has been approved successfully!', 'success')
    return redirect(url_for('companions'))

@app.post('/admin/companions/reject/<int:id>')
@admin_required
@permission_required('companion:verify')
def reject_companion(id):
    from models import CompanionProfile, Notification
    from flask import flash, redirect, url_for, request
    from extensions import db
    
    companion = CompanionProfile.query.filter_by(companion_id=id).first()
    if not companion:
        flash('Companion not found', 'error')
        return redirect(url_for('companions'))
    
    # Get rejection reason from form
    reason = request.form.get('reason', 'Your application did not meet our requirements.')
    
    # Update verification status
    companion.verification_status = VerificationStatusEnum.REJECTED
    
    # Create notification for companion
    notification = Notification(
        user_id=companion.user_id,
        title='Application Rejected',
        message=f'Unfortunately, your companion application has been rejected. Reason: {reason}',
        is_read=False
    )
    db.session.add(notification)
    db.session.commit()
    
    flash(f'{companion.display_name}\'s application has been rejected.', 'info')
    return redirect(url_for('companions'))

@app.post('/admin/companions/delete/<int:id>')
@admin_required
@permission_required('companion:delete')
def delete_companion(id):
    from models import CompanionProfile
    from flask import flash, redirect, url_for
    from extensions import db
    
    companion = CompanionProfile.query.filter_by(companion_id=id).first()
    if not companion:
        flash('Companion not found', 'error')
        return redirect(url_for('companions'))
    
    name = companion.display_name
    db.session.delete(companion)
    db.session.commit()
    
    flash(f'{name} has been deleted successfully.', 'success')
    return redirect(url_for('companions'))

@app.route('/admin/companions/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
@permission_required('companion:edit')
def edit_companion(id):
    from models import CompanionProfile, User
    from flask import flash, redirect, url_for, request
    from extensions import db
    
    companion = CompanionProfile.query.filter_by(companion_id=id).first()
    if not companion:
        flash('Companion not found', 'error')
        return redirect(url_for('companions'))
    
    if request.method == 'POST':
        # Update text fields
        companion.display_name = request.form.get('display_name')
        companion.age = int(request.form.get('age', companion.age))
        companion.location = request.form.get('location')
        companion.bio = request.form.get('bio')
        companion.rate_per_hour = float(request.form.get('rate_per_hour', companion.rate_per_hour))
        
        # Update status if provided
        new_status = request.form.get('verification_status')
        if new_status:
            companion.verification_status = new_status
            
        try:
            db.session.commit()
            flash(f'Profile for {companion.display_name} updated successfully!', 'success')
            return redirect(url_for('view_companion_detail', id=id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {str(e)}', 'error')
            
    # Get pending count for sidebar
    pending_count = CompanionProfile.query.filter_by(verification_status=VerificationStatusEnum.PENDING).count()
    
    return render_template(
        'admin/companion/edit.html',
        active_page='companions',
        companion=companion,
        user=companion.user,
        pending_count=pending_count
    )