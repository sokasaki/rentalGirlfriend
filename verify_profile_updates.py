import sys
import os

# Add the project directory to sys.path
sys.path.append(os.getcwd())

from app import app, db
from models.users import User
from models.customer_profiles import CustomerProfile
from models.companion_profiles import CompanionProfile
from flask import url_for

def test_profile_updates():
    with app.test_client() as client:
        # 1. Mock session for a customer
        # Note: We need to find a real user id from the DB or create one
        with app.app_context():
            customer_user = User.query.join(CustomerProfile).first()
            if not customer_user:
                print("No customer found for testing")
                return
            
            user_id = customer_user.user_id
            customer = CustomerProfile.query.filter_by(user_id=user_id).first()
            old_bio = customer.bio
            
            print(f"Testing Customer Profile Update (User ID: {user_id})")
        
        # Mock login by setting session
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['user_type'] = 'customer'
        
        # 2. Test Customer Update
        new_bio = "Updated Bio from Test Script"
        response = client.post('/update-profile-customer', data={
            'full_name': 'Test User Updated',
            'email': customer_user.email,
            'phone': customer_user.phone or '123456789',
            'location': 'Test Location',
            'bio': new_bio,
            'gender': 'MALE'
        }, follow_redirects=True)
        
        if response.status_code == 200:
            with app.app_context():
                updated_customer = CustomerProfile.query.filter_by(user_id=user_id).first()
                if updated_customer.bio == new_bio:
                    print("✅ Customer Profile update successful")
                else:
                    print("❌ Customer Profile update failed: Bio mismatch")
                    print(f"Expected: {new_bio}, Found: {updated_customer.bio}")
        else:
            print(f"❌ Customer Profile update request failed with status {response.status_code}")

        # 3. Repeat for Companion
        with app.app_context():
            companion_user = User.query.join(CompanionProfile).first()
            if not companion_user:
                print("No companion found for testing")
                return
            
            user_id = companion_user.user_id
            companion = CompanionProfile.query.filter_by(user_id=user_id).first()
            print(f"Testing Companion Profile Update (User ID: {user_id})")
            
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['user_type'] = 'companion'
            
        new_bio_comp = "Updated Companion Bio from Test"
        response = client.post('/update-profile-companion', data={
            'display_name': 'Comp Updated',
            'email': companion_user.email,
            'phone': companion_user.phone or '987654321',
            'age': 25,
            'rate_per_hour': 50,
            'location': 'Comp Location',
            'bio': new_bio_comp,
            'languages': ['English', 'Spanish'],
            'personality_traits': ['Outgoing', 'Friendly']
        }, follow_redirects=True)
        
        if response.status_code == 200:
            with app.app_context():
                updated_comp = CompanionProfile.query.filter_by(user_id=user_id).first()
                if updated_comp.bio == new_bio_comp:
                    print("✅ Companion Profile update successful")
                else:
                    print("❌ Companion Profile update failed: Bio mismatch")
        else:
            print(f"❌ Companion Profile update request failed with status {response.status_code}")

if __name__ == "__main__":
    test_profile_updates()
