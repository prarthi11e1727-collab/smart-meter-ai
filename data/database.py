import sqlite3
import os

# Database location
DB_FILE = os.path.join(
    os.path.dirname(__file__),
    "smartmeter.db"
)

# Connect to database
connection = sqlite3.connect(DB_FILE)

cursor = connection.cursor()

# Create table
cursor.execute("""
CREATE TABLE IF NOT EXISTS meter_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    voltage REAL,
    current REAL,
    power REAL,
    energy REAL
)
""")

connection.commit()
connection.close()

print("SQLite database created successfully!")
print("Database:", DB_FILE)