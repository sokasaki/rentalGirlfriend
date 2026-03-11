"""
One-off script to add the 'username' column to the users table.
SQLite cannot add UNIQUE columns via ALTER TABLE, so we add it plain
and backfill existing rows.
"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'instance', 'mydb.db')
if not os.path.exists(db_path):
    db_path = os.path.join(os.path.dirname(__file__), 'mydb.db')

print(f"Using database at: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check if column exists already
cursor.execute("PRAGMA table_info(users)")
columns = [col[1] for col in cursor.fetchall()]
print(f"Current columns: {columns}")

if 'username' not in columns:
    print("Adding 'username' column (no constraint, unique enforced by app)...")
    cursor.execute("ALTER TABLE users ADD COLUMN username VARCHAR(50)")
    conn.commit()
    print("Column added successfully!")
else:
    print("'username' column already exists, skipping ALTER TABLE.")

conn.close()
print("Done! Now re-seed the database to populate usernames.")
