from app import app, db
from models.customer_profiles import CustomerProfile

with app.app_context():
    profiles = CustomerProfile.query.all()
    print(f"Total profiles: {len(profiles)}")
    for p in profiles:
        print(f"ID: {p.customer_id}, UserID: {p.user_id}, Profile: {p.profile_photo}, Cover: {p.cover_photo}")
