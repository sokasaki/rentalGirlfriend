from app import app, db
from models import Role, Permission

def seed_permissions():
    """Seed initial permissions and assign them to the Admin role"""
    with app.app_context():
        # Ensure tables exist for new models
        db.create_all()
        
        # Define permissions
        permissions_list = [
            ("manage_users", "Can create, edit, and delete users"),
            ("manage_roles", "Can manage user roles and their permissions"),
            ("manage_companions", "Can manage and verify companion profiles"),
            ("manage_bookings", "Can view and manage booking requests"),
            ("manage_payments", "Can track payments and revenue"),
            ("manage_reports", "Can view and handle user reports"),
            ("manage_reviews", "Can manage and moderate reviews"),
            ("manage_broadcast", "Can send platform-wide notifications"),
            ("manage_analytics", "Can view performance metrics"),
            ("manage_settings", "Can update platform-wide system settings")
        ]
        
        # 1. Add permissions to database
        all_perms = []
        for name, desc in permissions_list:
            perm = Permission.query.filter_by(name=name).first()
            if not perm:
                perm = Permission(name=name, description=desc)
                db.session.add(perm)
                print(f"Added permission: {name}")
            all_perms.append(perm)
        
        db.session.commit()
        print("✓ All permissions ensured in database.")
        
        # 2. Assign all permissions to Admin role
        admin_role = Role.query.filter_by(role_name="Admin").first()
        if admin_role:
            added_count = 0
            for perm in all_perms:
                if perm not in admin_role.permissions:
                    admin_role.permissions.append(perm)
                    added_count += 1
            
            db.session.commit()
            if added_count > 0:
                print(f"✓ Assigned {added_count} new permissions to Admin role.")
            else:
                print("✓ Admin role already has all permissions.")
        else:
            print("✗ Error: Admin role not found. Please run seed_roles.py first.")

if __name__ == '__main__':
    seed_permissions()
