"""
Backfill usernames for existing users based on email prefixes and role data.
"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'instance', 'mydb.db')
if not os.path.exists(db_path):
    db_path = os.path.join(os.path.dirname(__file__), 'mydb.db')

print(f"Using database at: {db_path}")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all users with their emails and current usernames
cursor.execute("SELECT user_id, email, username FROM users")
users = cursor.fetchall()

# Known email -> username map from seed_data.py
email_username_map = {
    "admin@rentacompanion.com": "admin",
    "john@email.com": "johndoe",
    "michael@email.com": "michalsmith",
    "david@email.com": "davidwilson",
    "lisa@email.com": "lisaanderson",
    "sarah@email.com": "sarahj",
    "emma@email.com": "emmad",
    "olivia@email.com": "oliviam",
    "sophia@email.com": "sophial",
    "jessica@email.com": "jessicaw",
    "amanda@email.com": "amandab",
}

updated = 0
for user_id, email, existing_username in users:
    if existing_username:
        print(f"  User {user_id} ({email}) already has username '{existing_username}', skipping.")
        continue

    if email in email_username_map:
        new_username = email_username_map[email]
    else:
        # Fallback: use email prefix
        new_username = email.split('@')[0]

    cursor.execute("UPDATE users SET username = ? WHERE user_id = ?", (new_username, user_id))
    print(f"  Set username='{new_username}' for user {user_id} ({email})")
    updated += 1

conn.commit()
conn.close()
print(f"\nDone! Updated {updated} users.")
