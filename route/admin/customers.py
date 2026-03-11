from app import app, render_template, flash, redirect, url_for, admin_required
from models import User, CustomerProfile, Booking, CompanionProfile, CompanionPhoto
from extensions import db

@app.get('/admin/customers/view/<int:user_id>')
@admin_required
def view_customer(user_id):
    # Get user with customer info
    user = User.query.get_or_404(user_id)
    customer = CustomerProfile.query.filter_by(user_id=user_id).first()
    
    if not customer:
        flash('Customer profile not found for this user', 'error')
        return redirect(url_for('users'))
    
    # Get booking history for this customer
    bookings = Booking.query.filter_by(customer_id=customer.customer_id).order_by(Booking.start_time.desc()).all()
    
    # Get reviews written by this customer
    from models import Review
    reviews = Review.query.join(Booking).filter(Booking.customer_id == customer.customer_id).all()
    
    # Calculate stats
    total_spent = sum([float(b.total_price) for b in bookings if b.status.value in ['COMPLETED', 'PAID']])
    booking_count = len(bookings)
    
    # Get pending count for sidebar
    from models import CompanionProfile as CP
    pending_count = CP.query.filter_by(verification_status='PENDING').count()
    
    return render_template(
        'admin/customer/view_detail.html',
        active_page='users',
        user=user,
        customer=customer,
        bookings=bookings,
        reviews=reviews,
        photos=[],
        availability=[],
        total_spent=total_spent,
        booking_count=booking_count,
        pending_count=pending_count
    )
