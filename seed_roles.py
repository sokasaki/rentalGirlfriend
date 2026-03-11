from app import app, db
from models import Role

def seed_roles():
    """Seed initial roles into the database"""
    with app.app_context():
        # Check if roles already exist
        existing_roles = Role.query.count()
        if existing_roles > 0:
            print(f"Roles already exist ({existing_roles} roles found). Skipping seed.")
            return
        
        # Create initial roles
        roles = [
            Role(role_name="Admin"),
            Role(role_name="Customer"),
            Role(role_name="Companion")
        ]
        
        try:
            db.session.add_all(roles)
            db.session.commit()
            print("✓ Successfully seeded 3 roles: Admin, Customer, Companion")
        except Exception as e:
            db.session.rollback()
            print(f"✗ Error seeding roles: {str(e)}")

if __name__ == '__main__':
    seed_roles()
