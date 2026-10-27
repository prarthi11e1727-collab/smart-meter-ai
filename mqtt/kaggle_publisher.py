import json
import os
import ssl
import time
from pathlib import Path

import pandas as pd
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "train.csv"
load_dotenv(ROOT / ".env")

BROKER = os.getenv("HIVEMQ_HOST")
USERNAME = os.getenv("HIVEMQ_USER")
PASSWORD = os.getenv("HIVEMQ_PASS")
PORT = 8883
TOPIC = "smartmeter/kaggle/data"
BUILDING_ID = 107       # which building to replay
DELAY_SECONDS = 1       # seconds between readings

if not all([BROKER, USERNAME, PASSWORD]):
    raise SystemExit("Check HiveMQ credentials in your .env file.")
if not DATA_FILE.exists():
    raise SystemExit("data/train.csv not found.")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(USERNAME, PASSWORD)
client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS_CLIENT)


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("Connected to HiveMQ Cloud.")
    else:
        print("Connection failed:", reason_code)


client.on_connect = on_connect
client.connect(BROKER, PORT, 60)
client.loop_start()
time.sleep(2)

print("Replaying Kaggle readings for building", BUILDING_ID)
print("Topic:", TOPIC)
print("Press Ctrl+C to stop.")

try:
    for chunk in pd.read_csv(
        DATA_FILE,
        usecols=["building_id", "timestamp", "meter_reading", "anomaly"],
        chunksize=100000,
    ):
        chunk = chunk[chunk["building_id"] == BUILDING_ID]
        chunk = chunk.dropna(subset=["timestamp", "meter_reading", "anomaly"])
        if chunk.empty:
            continue

        for _, row in chunk.iterrows():
            message = {
                "timestamp": str(row["timestamp"]),
                "building_id": int(row["building_id"]),
                "meter_reading": float(row["meter_reading"]),
                "actual_anomaly": int(row["anomaly"]),
            }
            client.publish(TOPIC, json.dumps(message), qos=1)
            print("Sent:", json.dumps(message))
            time.sleep(DELAY_SECONDS)

except KeyboardInterrupt:
    print("\nKaggle replay stopped.")

finally:
    client.loop_stop()
    client.disconnect()