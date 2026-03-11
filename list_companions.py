from app import app, db
from models import CompanionProfile, User, Availability, CompanionPhoto

with app.app_context():
    print('='*80)
    print('COMPANION DATABASE OVERVIEW')
    print('='*80)
    
    companions = CompanionProfile.query.all()
    print(f'\nTotal Companions: {len(companions)}\n')
    
    for i, companion in enumerate(companions, 1):
        # Get availability count
        avail_count = Availability.query.filter_by(
            companion_id=companion.companion_id
        ).count()
        
        # Get available days
        availabilities = Availability.query.filter_by(
            companion_id=companion.companion_id
        ).all()
        
        available_days = sorted(set([avail.day_of_week.value for avail in availabilities]))
        
        # Get photo count
        photo_count = CompanionPhoto.query.filter_by(
            companion_id=companion.companion_id
        ).count()
        
        # Get user info
        user = User.query.get(companion.user_id)
        
        print(f'{i}. {companion.display_name}')
        print(f'   Email: {user.email if user else "N/A"}')
        print(f'   Age: {companion.age} | Gender: {companion.gender.value}')
        print(f'   Location: {companion.location}')
        print(f'   Rate: ${companion.rate_per_hour}/hour')
        print(f'   Verification: {companion.verification_status.value}')
        print(f'   Available Days: {", ".join(available_days) if available_days else "None"}')
        print(f'   Photos: {photo_count}')
        print(f'   Rating: {companion.avg_rating if companion.avg_rating else "No ratings"}')
        print()
    
    print('='*80)
    print('SUMMARY')
    print('='*80)
    print(f'Total Companions: {len(companions)}')
    approved = sum(1 for c in companions if c.verification_status.value == 'APPROVED')
    pending = sum(1 for c in companions if c.verification_status.value == 'PENDING')
    print(f'Approved: {approved}')
    print(f'Pending: {pending}')
    print('='*80)
