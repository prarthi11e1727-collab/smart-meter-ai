import paho.mqtt.client as mqtt
import ssl
import json
import csv
import os
import sqlite3

# HiveMQ Cloud
BROKER = "50b0ba49257044d3b4b3faf5c7c09cd3.s1.eu.hivemq.cloud"
PORT = 8883

USERNAME = "smartmeter"
PASSWORD = "12345678"

TOPIC = "smartmeter/data"

# CSV file
CSV_FILE = os.path.join(
    os.path.dirname(__file__),
    "..",
    "data",
    "synthetic_data.csv"
)

# SQLite database
DB_FILE = os.path.join(
    os.path.dirname(__file__),
    "..",
    "data",
    "smartmeter.db"
)


# Connect to SQLite
connection = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = connection.cursor()

print("Connected to SQLite database!")


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


# HiveMQ connection
def on_connect(client, userdata, flags, reason_code, properties):

    if reason_code == 0:
        print("Connected to HiveMQ Cloud!")
        client.subscribe(TOPIC)
        print("Subscribed to:", TOPIC)

    else:
        print("Connection failed:", reason_code)


# Receive MQTT data
def on_message(client, userdata, msg):

    try:

        data = json.loads(msg.payload.decode())

        print("Received:", data)

        # Save to SQLite
        cursor.execute("""
        INSERT INTO meter_data
        (timestamp, voltage, current, power, energy)
        VALUES (?, ?, ?, ?, ?)
        """, (
            data["timestamp"],
            data["voltage"],
            data["current"],
            data["power"],
            data["energy"]
        ))

        connection.commit()

        print("Saved to SQLite ✅")

        # Save to CSV also
        file_exists = os.path.exists(CSV_FILE)

        with open(CSV_FILE, "a", newline="") as file:

            writer = csv.writer(file)

            if not file_exists:
                writer.writerow([
                    "timestamp",
                    "voltage",
                    "current",
                    "power",
                    "energy"
                ])

            writer.writerow([
                data["timestamp"],
                data["voltage"],
                data["current"],
                data["power"],
                data["energy"]
            ])

    except Exception as e:

        print("Error:", e)


# MQTT client
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

client.username_pw_set(
    USERNAME,
    PASSWORD
)

# TLS
client.tls_set(
    cert_reqs=ssl.CERT_REQUIRED,
    tls_version=ssl.PROTOCOL_TLS_CLIENT
)

client.on_connect = on_connect
client.on_message = on_message

# Connect
client.connect(
    BROKER,
    PORT,
    60
)

print("Waiting for smart meter data...")

client.loop_forever()