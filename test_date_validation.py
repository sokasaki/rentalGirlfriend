import sys
import json
from app import app, db
from models import CompanionProfile, Availability
from datetime import datetime, timedelta

with app.app_context():
    print('='*70)
    print('DATE VALIDATION TEST')
    print('='*70)
    
    # Get companion and their availability
    companion = CompanionProfile.query.first()
    if companion:
        print(f'\nCompanion: {companion.display_name}')
        print(f'Companion ID: {companion.companion_id}')
        
        # Get availability
        availabilities = Availability.query.filter_by(
            companion_id=companion.companion_id
        ).all()
        
        available_days = set()
        print(f'\nAvailable Days & Times:')
        for avail in availabilities:
            available_days.add(avail.day_of_week.value)
            print(f'  • {avail.day_of_week.value}: {avail.start_time} - {avail.end_time}')
        
        print(f'\nAvailable Days Summary: {sorted(available_days)}')
        
        # Test validation logic
        print('\n' + '='*70)
        print('FRONTEND VALIDATION LOGIC')
        print('='*70)
        
        # Test dates
        test_dates = []
        
        # Find today and next 7 days
        today = datetime.now()
        day_names = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
        
        for i in range(7):
            test_date = today + timedelta(days=i)
            # Get day of week (0=Monday, 6=Sunday)
            weekday = test_date.weekday()
            # Convert to our format (0=Mon, 1=Tue, ..., 6=Sun)
            adjusted_day = weekday
            day_name = day_names[adjusted_day]
            
            is_available = day_name in available_days
            test_dates.append({
                'date': test_date.strftime('%Y-%m-%d'),
                'day': day_name,
                'available': is_available
            })
        
        print('\nDate Validation Results:')
        for test in test_dates:
            status = '✅ ALLOWED' if test['available'] else '❌ BLOCKED'
            print(f"  {test['date']} ({test['day']:<3}) {status}")
        
        print('\n' + '='*70)
        print('VALIDATION BEHAVIOR')
        print('='*70)
        print('When customer selects a date:')
        print('1. Frontend loads available_days from API')
        print('2. Real-time validation checks if day matches')
        print('   - If NO:  Shows error message + available days')
        print('   - If YES: Allows form submission')
        print('3. On form submit:')
        print('   - Validates date is in available_days array again')
        print('   - If validation fails: Shows warning popup')
        print('   - If validation passes: Sends booking to backend')
        print('4. Backend validates time slot')
        print('   - Calls _is_within_availability()')
        print('   - Final security check')
        print('\n' + '='*70)

