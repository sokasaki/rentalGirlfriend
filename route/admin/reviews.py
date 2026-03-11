from app import app, render_template, request, db, flash, redirect, url_for, admin_required, permission_required
from models import Review, Booking, CustomerProfile, CompanionProfile, ReviewStatusEnum, AuditLog
from sqlalchemy import func
from datetime import datetime
from flask import session

@app.get('/admin/reviews')
@admin_required
@permission_required('manage_reviews')
def reviews():
    # Get query parameters
    search_query = request.args.get('search', '').strip()
    rating_filter = request.args.get('rating', '')
    
    # Base query for reviews
    query = Review.query.join(Booking).join(CustomerProfile).join(CompanionProfile).order_by(Review.created_at.desc())
    
    # Apply rating filter
    if rating_filter:
        try:
            if rating_filter == '1-2':
                query = query.filter(Review.rating.in_([1, 2]))
            elif rating_filter == 'pending':
                query = query.filter(Review.status == ReviewStatusEnum.PENDING)
            elif rating_filter == 'approved':
                query = query.filter(Review.status == ReviewStatusEnum.APPROVED)
            elif rating_filter == 'rejected':
                query = query.filter(Review.status == ReviewStatusEnum.REJECTED)
            else:
                query = query.filter(Review.rating == int(rating_filter))
        except ValueError:
            pass
            
    # Apply search filter
    if search_query:
        query = query.filter(
            (CustomerProfile.full_name.ilike(f'%{search_query}%')) |
            (CompanionProfile.display_name.ilike(f'%{search_query}%')) |
            (Booking.booking_id.ilike(f'%{search_query}%'))
        )
        
    all_reviews = query.all()
    
    # Calculate stats
    total_reviews = Review.query.count()
    avg_rating = db.session.query(func.avg(Review.rating)).scalar() or 0
    
    # Distribution
    distribution = {}
    for i in range(1, 6):
        distribution[i] = Review.query.filter_by(rating=i).count()
        
    five_star_count = distribution.get(5, 0)
    
    # Pending moderation count
    pending_moderation = Review.query.filter(Review.status == ReviewStatusEnum.PENDING).count()
    
    # Get pending count for sidebar
    pending_count = CompanionProfile.query.filter_by(verification_status='PENDING').count()
    
    return render_template(
        'admin/reviews.html', 
        active_page='reviews', 
        reviews=all_reviews,
        total_reviews=total_reviews,
        avg_rating=round(float(avg_rating), 1),
        five_star_count=five_star_count,
        distribution=distribution,
        pending_moderation=pending_moderation,
        pending_count=pending_count,
        search_query=search_query,
        rating_filter=rating_filter
    )

@app.post('/admin/reviews/approve/<int:review_id>')
@admin_required
@permission_required('manage_reviews')
def approve_review(review_id):
    review = Review.query.get_or_404(review_id)
    review.status = ReviewStatusEnum.APPROVED
    review.moderated_at = datetime.utcnow()
    review.moderated_by = session.get('user_id')
    db.session.commit()
    
    # Log action
    AuditLog.log(
        user_id=session.get('user_id'),
        action='APPROVE_REVIEW',
        target_type='REVIEW',
        target_id=review_id,
        details=f"Approved review for booking #{review.booking_id}",
        ip_address=request.remote_addr
    )
    
    # Update companion average rating
    if review.booking and review.booking.companion:
        review.booking.companion.update_avg_rating()
        
    flash('Review has been approved and is now visible on the profile.', 'success')
    return redirect(url_for('reviews'))

@app.post('/admin/reviews/reject/<int:review_id>')
@admin_required
@permission_required('manage_reviews')
def reject_review(review_id):
    review = Review.query.get_or_404(review_id)
    review.status = ReviewStatusEnum.REJECTED
    review.moderated_at = datetime.utcnow()
    review.moderated_by = session.get('user_id')
    db.session.commit()
    
    # Log action
    AuditLog.log(
        user_id=session.get('user_id'),
        action='REJECT_REVIEW',
        target_type='REVIEW',
        target_id=review_id,
        details=f"Rejected review for booking #{review.booking_id}",
        ip_address=request.remote_addr
    )
    
    # Update companion average rating
    if review.booking and review.booking.companion:
        review.booking.companion.update_avg_rating()
        
    flash('Review has been rejected.', 'warning')
    return redirect(url_for('reviews'))

@app.post('/admin/reviews/delete/<int:review_id>')
@admin_required
@permission_required('manage_reviews')
def delete_review(review_id):
    review = Review.query.get_or_404(review_id)
    companion = review.booking.companion if review.booking else None
    
    db.session.delete(review)
    db.session.commit()
    
    # Log action
    AuditLog.log(
        user_id=session.get('user_id'),
        action='DELETE_REVIEW',
        target_type='REVIEW',
        target_id=review_id,
        details=f"Deleted review for booking #{review.booking_id if review.booking else 'N/A'}",
        ip_address=request.remote_addr
    )
    
    # Update companion average rating
    if companion:
        companion.update_avg_rating()
        
    flash('Review has been deleted.', 'success')
    return redirect(url_for('reviews'))