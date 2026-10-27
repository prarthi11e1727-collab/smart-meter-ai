
import json
import os
import ssl
import sqlite3
from pathlib import Path

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

BROKER = os.getenv("HIVEMQ_HOST")
USERNAME = os.getenv("HIVEMQ_USER")
PASSWORD = os.getenv("HIVEMQ_PASS")
TOPIC = "smartmeter/kaggle/data"
DB_FILE = ROOT / "data" / "smartmeter.db"

if not all([BROKER, USERNAME, PASSWORD]):
    raise SystemExit("Missing HiveMQ credentials in .env")

connection = sqlite3.connect(DB_FILE, check_same_thread=False)
connection.execute("""
CREATE TABLE IF NOT EXISTS kaggle_meter_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    building_id INTEGER,
    meter_reading REAL,
    predicted_anomaly INTEGER,
    actual_anomaly INTEGER,
    data_source TEXT
)
""")
connection.commit()

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("Connected to HiveMQ!")
        client.subscribe(TOPIC)
        print("Subscribed to:", TOPIC)
    else:
        print("Connection failed:", reason_code)

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        connection.execute("""
        INSERT INTO kaggle_meter_data
        (timestamp, building_id, meter_reading,
         predicted_anomaly, actual_anomaly, data_source)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data["timestamp"], data["building_id"],
            data["meter_reading"], data["predicted_anomaly"],
            data["actual_anomaly"], data["data_source"]
        ))
        connection.commit()
        print(
            f"Saved building {data['building_id']} | "
            f"reading {data['meter_reading']} | "
            f"prediction {data['predicted_anomaly']}"
        )
    except Exception as e:
        print("Error:", e)

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(USERNAME, PASSWORD)
client.tls_set(
    cert_reqs=ssl.CERT_REQUIRED,
    tls_version=ssl.PROTOCOL_TLS_CLIENT
)
client.on_connect = on_connect
client.on_message = on_message

try:
    client.connect(BROKER, 8883, 60)
    print("Waiting for Kaggle readings...")
    client.loop_forever()
except KeyboardInterrupt:
    print("Subscriber stopped.")
finally:
    connection.close()
    client.disconnect()
