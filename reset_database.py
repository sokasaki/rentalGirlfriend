"""Reset database by removing it and recreating migrations"""
import os
import shutil
from pathlib import Path

# Get paths
instance_dir = Path('instance')
migrations_dir = Path('migrations/versions')
db_file = instance_dir / 'mydb.db'

print("Resetting database...")

# Remove database file
if db_file.exists():
    try:
        os.remove(db_file)
        print(f"✓ Deleted {db_file}")
    except PermissionError:
        print(f"❌ Cannot delete {db_file} - file is in use!")
        print("   Please close any running Flask apps and try again.")
        exit(1)

# Remove migration version files (keep the directory structure)
if migrations_dir.exists():
    for file in migrations_dir.glob('*.py'):
        if file.name != '__init__.py':
            os.remove(file)
            print(f"✓ Deleted {file}")
    
    # Remove pycache
    pycache = migrations_dir / '__pycache__'
    if pycache.exists():
        shutil.rmtree(pycache)
        print(f"✓ Deleted {pycache}")

print("\n✅ Database reset complete!")
print("\nNext steps:")
print("1. Run: flask db migrate -m 'Initial migration'")
print("2. Run: flask db upgrade")
print("3. Run: python seed_roles.py")
print("4. Run: python seed_data.py")
