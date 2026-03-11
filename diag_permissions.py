from app import app, db
from models import Role, Permission, User

def diag():
    with app.app_context():
        print("--- ROLES ---")
        roles = Role.query.all()
        for r in roles:
            perms = [p.name for p in r.permissions]
            print(f"Role: {r.role_name} (ID: {r.role_id})")
            print(f"  Permissions: {', '.join(perms) if perms else 'None'}")
            print(f"  Users: {len(r.users)}")
            
        print("\n--- PERMISSIONS ---")
        perms = Permission.query.all()
        print(f"Total permissions: {len(perms)}")

if __name__ == '__main__':
    diag()
