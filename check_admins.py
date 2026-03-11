from app import app
from extensions import db
from models.users import User
from models.roles import Role

with app.app_context():
    admins = User.query.join(Role).all()
    print("All users with roles:")
    for u in admins:
        print(f"Email: {u.email}, Role: {u.role.role_name if u.role else 'None'}")
    
    admin_users = User.query.join(Role).filter(Role.role_name == 'Admin').all()
    print("\nAdmin users:")
    for u in admin_users:
        print(f"Email: {u.email}")
