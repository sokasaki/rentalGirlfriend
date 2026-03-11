from app import app, db
from models.users import User
from models.roles import Role
from models.customer_profiles import CustomerProfile

with app.app_context():
    print("--- Database Diagnostics ---")
    users = User.query.all()
    for u in users:
        role_name = u.role.role_name if u.role else "N/A"
        customer_name = u.customer_profile.full_name if u.customer_profile else "N/A"
        print(f"User ID: {u.user_id} | Username: {u.username} | Role: {role_name} | Customer Profile: {customer_name}")
        print(f"  display_name property returns: '{u.display_name}'")
        if u.role:
            print(f"  Role ID: {u.role_id} | Role Name (Raw): '{u.role.role_name}'")
        print("-" * 30)
