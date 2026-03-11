#!/usr/bin/env python
"""Test script to diagnose booking POST error"""

import requests
import json
from datetime import datetime, timedelta

# Test companion from database (ID 1 = Sarah Johnson)
COMPANION_ID = 1

# Create a booking request for a future available date
# Sarah is available: MON, WED, THU, FRI from 09:00-22:00
# Today is Monday Feb 24, 2026
# Available dates: Feb 25 (WED), Feb 26 (THU), Feb 27 (FRI), Mar 02 (MON)

tomorrow = datetime.now() + timedelta(days=1)  # Feb 25, 2026 (Wednesday)

booking_data = {
    'companion_id': str(COMPANION_ID),
    'date': tomorrow.strftime('%Y-%m-%d'),  # 2026-02-25
    'time': '14:00',  # 2:00 PM (within 09:00-22:00)
    'duration': '2',  # 2 hours
    'location': 'Coffee Shop Downtown',
    'notes': 'Looking forward to meeting'
}

print("Testing booking POST request...")
print(f"Payload: {json.dumps(booking_data, indent=2)}")
print()

try:
    # First need to login to get session
    # Let's check if we have a valid session by visiting the profile page
    session = requests.Session()
    
    # Try posting to the endpoint
    response = session.post(
        'http://localhost:5000/create_booking',
        json=booking_data,
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code != 201 and response.status_code != 200:
        print(f"\n❌ Error: Got {response.status_code} instead of success")
        try:
            data = response.json()
            print(f"Error message: {data.get('message', 'No message')}")
        except:
            pass
            
except Exception as e:
    print(f"Connection error: {e}")
