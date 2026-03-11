import sqlite3
import os

db_path = "d:/python/Rental-V1/rentalGirlfriend/instance/mydb.db"
if not os.path.exists(db_path):
    print(f"Checking {db_path} - Not found, trying mydb.db in root")
    db_path = "d:/python/Rental-V1/rentalGirlfriend/mydb.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(customer_profiles)")
columns = cursor.fetchall()
print(f"Columns in customer_profiles:")
for col in columns:
    print(col)
conn.close()
