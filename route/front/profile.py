from app import app, render_template, db
from models.companion_profiles import CompanionProfile
from models.companion_photos import CompanionPhoto
from models.reviews import Review, ReviewStatusEnum
from models.favorites import Favorite
from models.customer_profiles import CustomerProfile
from flask import abort, session
import json

@app.get('/profile')
@app.get('/profile/<int:companion_id>')
def profile(companion_id=None):
    if companion_id:
        # Get companion from database
        companion = CompanionProfile.query.filter_by(companion_id=companion_id).first()
        if not companion:
            abort(404)
        
        # Get primary photo or first photo
        primary_photo = CompanionPhoto.query.filter_by(
            companion_id=companion_id, 
            is_primary=True
        ).first()
        
        if not primary_photo:
            primary_photo = CompanionPhoto.query.filter_by(companion_id=companion_id).first()
            
        photo_url = primary_photo.main_url if primary_photo else '/static/images/avatar-placeholder.jpg'
        
        # Get all photos
        photos = CompanionPhoto.query.filter_by(companion_id=companion_id).all()
        
        # Get reviews with customer info
        from models.bookings import Booking
        from models.customer_profiles import CustomerProfile
        
        reviews = db.session.query(Review).join(
            Booking, Review.booking_id == Booking.booking_id
        ).filter(
            Booking.companion_id == companion_id,
            Review.status == ReviewStatusEnum.APPROVED
        ).order_by(Review.created_at.desc()).limit(10).all()
        
        total_approved_reviews = db.session.query(Review).join(
            Booking, Review.booking_id == Booking.booking_id
        ).filter(
            Booking.companion_id == companion_id,
            Review.status == ReviewStatusEnum.APPROVED
        ).count()
        
        # Format reviews with customer names
        formatted_reviews = []
        for review in reviews:
            customer_photo = "/static/images/avatar-placeholder.jpg"
            if review.booking and review.booking.customer:
                customer_name = review.booking.customer.full_name or "Anonymous"
                customer_photo = review.booking.customer.thumbnail_url or "/static/images/avatar-placeholder.jpg"
            
            formatted_reviews.append({
                'customer_name': customer_name,
                'customer_photo': customer_photo,
                'rating': review.rating,
                'comment': review.comment,
                'reply': review.reply,
                'replied_at': review.replied_at,
                'created_at': review.created_at
            })
        
        # Parse personality traits if stored as JSON
        personality_traits = []
        if companion.personality_traits:
            if isinstance(companion.personality_traits, str):
                try:
                    personality_traits = json.loads(companion.personality_traits)
                except:
                    personality_traits = []
            else:
                personality_traits = companion.personality_traits

        # Parse languages to list + display string
        languages_list = []
        if companion.languages:
            if isinstance(companion.languages, str):
                try:
                    parsed_languages = json.loads(companion.languages)
                    if isinstance(parsed_languages, list):
                        languages_list = parsed_languages
                    elif parsed_languages:
                        languages_list = [str(parsed_languages)]
                except:
                    languages_list = [companion.languages]
            elif isinstance(companion.languages, list):
                languages_list = companion.languages
            else:
                languages_list = [str(companion.languages)]

        if not languages_list:
            languages_list = ["English"]

        # Build weekly availability structure for UI
        availability_order = [
            ("MON", "Monday", "MON"),
            ("TUE", "Tuesday", "TUE"),
            ("WED", "Wednesday", "WED"),
            ("THU", "Thursday", "THU"),
            ("FRI", "Friday", "FRI"),
            ("SAT", "Saturday", "SAT"),
            ("SUN", "Sunday", "SUN"),
        ]

        availability_map = {code: [] for code, _, _ in availability_order}
        for slot in companion.availabilities:
            day_code = slot.day_of_week.value if slot.day_of_week else None
            if day_code in availability_map:
                availability_map[day_code].append({
                    'start': slot.start_time.strftime('%I:%M %p').lstrip('0'),
                    'end': slot.end_time.strftime('%I:%M %p').lstrip('0')
                })

        availability_week = []
        for code, day_name, short_name in availability_order:
            day_slots = sorted(availability_map[code], key=lambda item: item['start'])
            availability_week.append({
                'code': code,
                'day_name': day_name,
                'short_name': short_name,
                'slots': day_slots,
                'is_available': len(day_slots) > 0
            })
        
        # Parse location
        location_parts = (companion.location or '').split(',')
        city = location_parts[0].strip() if len(location_parts) > 0 else 'N/A'
        state = location_parts[1].strip() if len(location_parts) > 1 else ''
        
        companion_data = {
            'companion_id': companion.companion_id,
            'user_id': companion.user_id,
            'display_name': companion.display_name,
            'age': companion.age,
            'gender': companion.gender.value if companion.gender else 'Not specified',
            'bio': companion.bio or 'No bio available',
            'rate_per_hour': float(companion.rate_per_hour),
            'location': companion.location,
            'city': city,
            'state': state,
            'languages': languages_list,
            'languages_display': ', '.join(languages_list),
            'personality_traits': personality_traits,
            'availability_week': availability_week,
            'avg_rating': round(float(companion.avg_rating or 0), 1),
            'total_reviews': total_approved_reviews,
            'verification_status': companion.verification_status.value if companion.verification_status else 'PENDING',
            'photo_url': photo_url,
            'user': {
                'email': companion.user.email if companion.user else 'N/A',
                'phone': companion.user.phone if companion.user else 'N/A'
            },
            'photos': [{
                'photo_url': p.photo_url,
                'main_url': p.main_url,
                'thumbnail_url': p.thumbnail_url,
                'is_primary': p.is_primary
            } for p in photos],
            'reviews': formatted_reviews
        }
        
        # Check if the current logged-in user has favorited this companion
        is_favorited = False
        user_id = session.get('user_id')
        if user_id:
            customer = CustomerProfile.query.filter_by(user_id=user_id).first()
            if customer:
                is_favorited = Favorite.query.filter_by(
                    customer_id=customer.customer_id,
                    companion_id=companion_id
                ).first() is not None

        return render_template(
            'front/pages/profile.html',
            companion=companion_data,
            photos=photos,
            is_favorited=is_favorited
        )
    else:
        # Default profile page for logged-in user (if needed)
        return render_template('front/pages/profile.html')
