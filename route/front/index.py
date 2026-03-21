from app import app, render_template, db
from models.companion_profiles import CompanionProfile, VerificationStatusEnum
from models.bookings import Booking, BookingStatusEnum
from models.reviews import Review
from models.customer_profiles import CustomerProfile
from models.users import User
from models.companion_photos import CompanionPhoto
from sqlalchemy import func
import json

@app.get('/')
@app.get('/home')
def home():
    # Get featured companions (top 4 by rating)
    featured_companions_query = db.session.query(CompanionProfile).filter_by(
        verification_status=VerificationStatusEnum.APPROVED
    ).order_by(CompanionProfile.avg_rating.desc()).limit(4).all()
    
    # Format featured companions
    featured_companions = []
    for companion in featured_companions_query:
        # Get primary photo via model property
        photo_url = companion.primary_main_url or '/static/images/avatar-placeholder.jpg'

        
        # Parse personality traits
        try:
            if isinstance(companion.personality_traits, str):
                personality_traits = json.loads(companion.personality_traits)
            else:
                personality_traits = companion.personality_traits or []
        except:
            personality_traits = []
        
        featured_companions.append({
            'companion_id': companion.companion_id,
            'display_name': companion.display_name,
            'age': companion.age,
            'bio': companion.bio,
            'photo_url': photo_url,
            'avg_rating': float(companion.avg_rating) if companion.avg_rating else 0,
            'rate_per_hour': float(companion.rate_per_hour),
            'personality_traits': personality_traits[:2]  # First 2 traits
        })
    
    # Calculate site statistics
    total_companions = db.session.query(func.count(CompanionProfile.companion_id)).filter_by(
        verification_status=VerificationStatusEnum.APPROVED
    ).scalar() or 0
    
    total_bookings = db.session.query(func.count(Booking.booking_id)).filter(
        Booking.status.in_([BookingStatusEnum.COMPLETED, BookingStatusEnum.PAID, BookingStatusEnum.APPROVED])
    ).scalar() or 0
    
    avg_rating = db.session.query(func.avg(CompanionProfile.avg_rating)).filter(
        CompanionProfile.verification_status == VerificationStatusEnum.APPROVED,
        CompanionProfile.avg_rating.isnot(None)
    ).scalar() or 0
    
    # Get recent testimonials (top 3 reviews with highest ratings)
    testimonials_query = db.session.query(Review, Booking, CustomerProfile, User).join(
        Booking, Review.booking_id == Booking.booking_id
    ).join(
        CustomerProfile, Booking.customer_id == CustomerProfile.customer_id
    ).join(
        User, CustomerProfile.user_id == User.user_id
    ).filter(
        Review.rating >= 4,
        Review.comment.isnot(None)
    ).order_by(Review.rating.desc(), Review.created_at.desc()).limit(3).all()
    
    # Format testimonials
    testimonials = []
    for review, booking, customer, user in testimonials_query:
        testimonials.append({
            'customer_name': customer.full_name or 'Anonymous',
            'customer_photo': 'https://i.pravatar.cc/100?img=' + str(booking.customer_id % 70),
            'rating': review.rating,
            'comment': review.comment,
            'title': 'Verified Client'  # Could be enhanced with actual user role
        })
    
    # Fill with default testimonials if not enough reviews
    while len(testimonials) < 3:
        testimonials.append({
            'customer_name': 'Happy Client',
            'customer_photo': 'https://i.pravatar.cc/100?img=' + str(len(testimonials) + 1),
            'rating': 5,
            'comment': 'Great experience! Highly recommend this service.',
            'title': 'Verified Client'
        })
    
    from flask import session
    from models.favorites import Favorite
    
    # Get the set of companion IDs the current user has favorited
    favorited_ids = set()
    user_id = session.get('user_id')
    if user_id:
        customer = CustomerProfile.query.filter_by(user_id=user_id).first()
        if customer:
            favs = Favorite.query.filter_by(customer_id=customer.customer_id).all()
            favorited_ids = {f.companion_id for f in favs}

    return render_template('front/index.html',
        featured_companions=featured_companions,
        total_companions=total_companions,
        total_bookings=total_bookings,
        avg_rating=float(avg_rating) if avg_rating else 0,
        testimonials=testimonials,
        favorited_ids=favorited_ids
    )
