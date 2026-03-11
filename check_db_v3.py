from app import app, db
from models.customer_profiles import CustomerProfile

with app.app_context():
    profiles = CustomerProfile.query.all()
    print(f"DEBUG: Found {len(profiles)} profiles")
    for p in profiles:
        print(f"--- Customer ID: {p.customer_id} ---")
        print(f"User ID: {p.user_id}")
        print(f"Profile Photo: {p.profile_photo}")
        print(f"Cover Photo:   {p.cover_photo}")
