from app import app, db
from models.users import User
from models.customer_profiles import CustomerProfile

with app.app_context():
    print("--- Searching for John Doe ---")
    customer = CustomerProfile.query.filter(CustomerProfile.full_name.ilike('%John Doe%')).first()
    if customer:
        user = customer.user
        role_name = user.role.role_name if user.role else "N/A"
        print(f"User ID: {user.user_id}")
        print(f"Username: {user.username}")
        print(f"Role: {role_name}")
        print(f"Full Name: {customer.full_name}")
        print(f"display_name returns: '{user.display_name}'")
    else:
        print("John Doe not found in CustomerProfile.")

    print("\n--- Current Session User Hint ---")
    # Since I can't check session directly here, I'll list all users with Admin role
    admins = User.query.join(User.role).filter(User.role.role_name == 'Admin').all()
    for a in admins:
        cp_name = a.customer_profile.full_name if a.customer_profile else "None"
        print(f"Admin User: {a.username} | Customer Profile Name: {cp_name} | display_name: {a.display_name}")
