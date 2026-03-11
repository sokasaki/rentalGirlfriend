import sqlite3
import os

db_path = os.path.join('instance', 'mydb.db')
if not os.path.exists(db_path):
    print(f"Error: {db_path} not found.")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE bookings ADD COLUMN created_at DATETIME;")
    conn.commit()
    print("Column 'created_at' added successfully to 'bookings' table.")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e).lower():
        print("Column 'created_at' already exists.")
    else:
        print(f"Error: {e}")
finally:
    conn.close()
