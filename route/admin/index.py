from app import app, render_template, db, admin_required
from models.users import User
from models.companion_profiles import CompanionProfile, VerificationStatusEnum
from models.bookings import Booking, BookingStatusEnum
from models.payments import Payment, PaymentStatusEnum
from models.companion_photos import CompanionPhoto
from datetime import datetime, timedelta
from sqlalchemy import func

@app.get('/admin')
@app.get('/admin/home')
@admin_required
def admin_home():
    # Calculate statistics
    total_users = User.query.count()
    
    active_companions = CompanionProfile.query.filter(
        CompanionProfile.verification_status == VerificationStatusEnum.APPROVED
    ).count()
    
    total_bookings = Booking.query.count()
    
    # Revenue - sum of completed payments
    monthly_revenue = db.session.query(func.sum(Payment.amount)).filter(
        Payment.status == PaymentStatusEnum.PAID
    ).scalar() or 0
    
    # Pending companions for approval
    pending_companions_data = []
    pending_companions = CompanionProfile.query.filter(
        CompanionProfile.verification_status == VerificationStatusEnum.PENDING
    ).limit(5).all()
    
    for companion in pending_companions:
        # Get companion's primary photo
        companion_photo = None
        if companion.photos:
            primary = [p for p in companion.photos if p.is_primary]
            companion_photo = primary[0].photo_url if primary else (companion.photos[0].photo_url if companion.photos else None)
        
        pending_companions_data.append({
            'companion_id': companion.companion_id,
            'display_name': companion.display_name,
            'avatar': companion_photo,
            'user_email': companion.user.email if companion.user else 'N/A',
            'user_phone': companion.user.phone if companion.user else 'N/A',
            'age': companion.age,
            'location': companion.location,
            'languages': ', '.join(companion.languages) if companion.languages else 'N/A',
            'bio': companion.bio or 'No bio provided.',
            'applied_date': companion.user.created_at if companion.user else None
        })
    
    # Revenue analytics
    now = datetime.now()
    this_month_start = now.replace(day=1)
    last_month_end = this_month_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    
    this_month_revenue = db.session.query(func.sum(Payment.amount)).filter(
        Payment.status == PaymentStatusEnum.PAID,
        Payment.paid_at >= this_month_start
    ).scalar() or 0
    
    last_month_revenue = db.session.query(func.sum(Payment.amount)).filter(
        Payment.status == PaymentStatusEnum.PAID,
        Payment.paid_at >= last_month_start,
        Payment.paid_at < this_month_start
    ).scalar() or 0
    
    # Calculate month growth percentage
    if last_month_revenue > 0:
        month_growth_percent = int(((this_month_revenue - last_month_revenue) / last_month_revenue) * 100)
    else:
        month_growth_percent = 0
    
    # Platform statistics
    completed_bookings = Booking.query.filter(
        Booking.status == BookingStatusEnum.COMPLETED
    ).count()
    total_bookings_for_rate = total_bookings if total_bookings > 0 else 1
    success_rate = int((completed_bookings / total_bookings_for_rate) * 100)
    
    # Average rating from companions
    avg_rating_result = db.session.query(func.avg(CompanionProfile.avg_rating)).filter(
        CompanionProfile.avg_rating.isnot(None)
    ).scalar()
    avg_rating = round(float(avg_rating_result), 1) if avg_rating_result else 0
    
    # Active users today (created in last 24 hours)
    yesterday = now - timedelta(days=1)
    active_today = User.query.filter(User.created_at >= yesterday).count()
    
    # New signups this month
    new_signups = User.query.filter(User.created_at >= this_month_start).count()
    
    # Get pending count for sidebar badge
    pending_count = CompanionProfile.query.filter_by(verification_status='PENDING').count()
    
    return render_template(
        'admin/index.html',
        active_page='home',
        total_users=total_users,
        active_companions=active_companions,
        total_bookings=total_bookings,
        monthly_revenue=float(monthly_revenue),
        pending_companions=pending_companions_data,
        pending_count=pending_count,
        this_month_revenue=float(this_month_revenue),
        last_month_revenue=float(last_month_revenue),
        month_growth_percent=month_growth_percent,
        success_rate=success_rate,
        avg_rating=avg_rating,
        active_today=active_today,
        new_signups=new_signups
    )