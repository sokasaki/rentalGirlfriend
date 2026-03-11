#!/usr/bin/env python3
"""KHQR Setup Verification Script"""

from app import app
from route.khqr_routes import _get_khqr_service

print("=" * 50)
print("KHQR SETUP VERIFICATION")
print("=" * 50)

# Config check
print("\n✓ Configuration loaded from .env.example:")
print(f"  - KHQR_ENABLED: {app.config.get('KHQR_ENABLED')}")
khqr_token = app.config.get('KHQR_TOKEN', '')
print(f"  - KHQR_TOKEN: {'Present (' + str(len(khqr_token)) + ' chars)' if khqr_token else 'MISSING'}")
print(f"  - KHQR_BANK_ACCOUNT: {app.config.get('KHQR_BANK_ACCOUNT') or 'MISSING'}")
print(f"  - KHQR_MERCHANT_NAME: {app.config.get('KHQR_MERCHANT_NAME')}")

# Service factory check
service = _get_khqr_service()
print(f"\n✓ Service Factory:")
print(f"  - Service initialized: {service is not None}")
print(f"  - Service type: {type(service).__name__}")

# Endpoint check
client = app.test_client()
resp = client.post('/khqr/checkout', json={'booking_id': 999})
print(f"\n✓ Endpoint Status (without auth):")
print(f"  - HTTP Status: {resp.status_code}")
print(f"  - Expected: 401 Unauthorized (not 503 config error)")
print(f"  - Response: {resp.get_json()}")

print("\n" + "=" * 50)
if resp.status_code == 401:
    print("✅ RESULT: KHQR service is properly configured!")
else:
    print(f"❌ RESULT: Unexpected status {resp.status_code}")
print("=" * 50)
