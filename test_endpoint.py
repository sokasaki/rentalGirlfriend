#!/usr/bin/env python3
from app import app
import json

print("Testing /khqr/checkout endpoint with test client:")
print("=" * 60)

with app.test_client() as client:
    # Test 1: Without auth
    resp = client.post('/khqr/checkout', 
                       data=json.dumps({'booking_id': 1}),
                       headers={'Content-Type': 'application/json'})
    print(f"Status (no auth): {resp.status_code}")
    print(f"Response: {resp.get_json()}")
    
print("\n" + "=" * 60)
print("Testing with valid session (logged in):")

with app.test_client() as client:
    with client.session_transaction() as sess:
        sess['user_id'] = 1
    
    resp = client.post('/khqr/checkout',
                       data=json.dumps({'booking_id': 999}),
                       headers={'Content-Type': 'application/json'})
    print(f"Status (with auth): {resp.status_code}")
    print(f"Response: {resp.get_json()}")

print("\n" + "=" * 60)
print("Checking service factory in route context:")

from route.khqr_routes import _get_khqr_service
svc = _get_khqr_service()
print(f"Service from factory: {svc is not None}")
print(f"Service type: {type(svc).__name__ if svc else 'None'}")
