from app import app, render_template, db
from models.companion_profiles import CompanionProfile, VerificationStatusEnum
from models.companion_photos import CompanionPhoto
from models.favorites import Favorite
from models.customer_profiles import CustomerProfile
from flask import request, session
from sqlalchemy import func
from models.reviews import Review, ReviewStatusEnum
from models.bookings import Booking
import json

@app.get('/listing')
@app.get('/companions')
def listing():
    # Get all approved companions for filter options
    all_approved = CompanionProfile.query.filter(
        CompanionProfile.verification_status == VerificationStatusEnum.APPROVED
    ).all()
    
    # Extract unique personality traits from all companions
    all_traits = set()
    for companion in all_approved:
        if companion.personality_traits:
            if isinstance(companion.personality_traits, list):
                all_traits.update(companion.personality_traits)
            elif isinstance(companion.personality_traits, str):
                try:
                    traits = json.loads(companion.personality_traits)
                    if isinstance(traits, list):
                        all_traits.update(traits)
                except:
                    pass
    
    available_traits = sorted(list(all_traits))
    
    # Get min/max price from database
    price_stats = db.session.query(
        func.min(CompanionProfile.rate_per_hour),
        func.max(CompanionProfile.rate_per_hour)
    ).filter(
        CompanionProfile.verification_status == VerificationStatusEnum.APPROVED
    ).first()
    
    min_available_price = float(price_stats[0] or 20) if price_stats[0] else 20
    max_available_price = float(price_stats[1] or 200) if price_stats[1] else 200
    
    # Get filter parameters
    search = request.args.get('search', '').strip()
    min_price = request.args.get('min_price', type=float, default=min_available_price)
    max_price = request.args.get('max_price', type=float, default=max_available_price)
    personality = request.args.get('personality', '').split(',') if request.args.get('personality') else []
    age_range = request.args.get('age_range', '')
    sort_by = request.args.get('sort', 'featured')
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    # Start with approved companions only
    query = CompanionProfile.query.filter(
        CompanionProfile.verification_status == VerificationStatusEnum.APPROVED
    )
    
    # Apply search filter
    if search:
        query = query.filter(
            db.or_(
                CompanionProfile.display_name.ilike(f'%{search}%'),
                CompanionProfile.bio.ilike(f'%{search}%')
            )
        )
    
    # Apply price range filter
    query = query.filter(
        CompanionProfile.rate_per_hour >= min_price,
        CompanionProfile.rate_per_hour <= max_price
    )
    
    # Apply age range filter
    if age_range:
        if age_range == '18-24':
            query = query.filter(CompanionProfile.age.between(18, 24))
        elif age_range == '25-30':
            query = query.filter(CompanionProfile.age.between(25, 30))
        elif age_range == '31-35':
            query = query.filter(CompanionProfile.age.between(31, 35))
        elif age_range == '36+':
            query = query.filter(CompanionProfile.age >= 36)
    
    # Apply personality filter
    if personality and personality[0]:
        personality_filters = [f'%{p.strip().lower()}%' for p in personality if p.strip()]
        filters = []
        for p_filter in personality_filters:
            filters.append(db.func.lower(CompanionProfile.personality_traits).contains(p_filter))
        if filters:
            query = query.filter(db.or_(*filters))
    
    # Apply sorting
    if sort_by == 'price_low':
        query = query.order_by(CompanionProfile.rate_per_hour.asc())
    elif sort_by == 'price_high':
        query = query.order_by(CompanionProfile.rate_per_hour.desc())
    elif sort_by == 'rating':
        query = query.order_by(CompanionProfile.avg_rating.desc())
    else:  # featured (default)
        query = query.order_by(CompanionProfile.avg_rating.desc())
    
    # Get paginated results
    total_companions = query.count()
    pagination = query.paginate(page=page, per_page=per_page)
    companions_list = pagination.items
    
    # Format companion data for template
    companions = []
    for companion in companions_list:
        # Get primary photo via model property
        photo_url = companion.primary_main_url or '/static/images/avatar-placeholder.jpg'

        
        # Get review count for trust signals
        reviews_count = Review.query.join(Booking).filter(
            Booking.companion_id == companion.companion_id,
            Review.status == ReviewStatusEnum.APPROVED
        ).count()
        
        companions.append({
            'companion_id': companion.companion_id,
            'display_name': companion.display_name,
            'age': companion.age,
            'bio': companion.bio[:150] + '...' if len(companion.bio or '') > 150 else companion.bio,
            'rate_per_hour': float(companion.rate_per_hour),
            'avg_rating': round(float(companion.avg_rating or 4.5), 1),
            'photo_url': photo_url,
            'personality_traits': companion.personality_traits or [],
            'location': companion.location or 'Unknown',
            'reviews_count': reviews_count
        })
    
    # Get the set of companion IDs the current user has favorited
    favorited_ids = set()
    user_id = session.get('user_id')
    if user_id:
        customer = CustomerProfile.query.filter_by(user_id=user_id).first()
        if customer:
            favs = Favorite.query.filter_by(customer_id=customer.customer_id).all()
            favorited_ids = {f.companion_id for f in favs}

    return render_template(
        'front/pages/listing.html',
        companions=companions,
        total_companions=total_companions,
        current_page=page,
        total_pages=pagination.pages,
        has_prev=pagination.has_prev,
        has_next=pagination.has_next,
        search=search,
        min_price=min_price,
        max_price=max_price,
        age_range=age_range,
        sort_by=sort_by,
        min_available_price=int(min_available_price),
        max_available_price=int(max_available_price),
        available_traits=available_traits,
        personality=personality,
        favorited_ids=favorited_ids
    )
