
import json
import time
from pathlib import Path

import joblib
import pandas as pd
import paho.mqtt.client as mqtt
from dotenv import load_dotenv
import os
import ssl

# Project paths
ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "train.csv"
MODEL_FILE = ROOT / "ai" / "kaggle_anomaly_model.joblib"

# MQTT configuration from your existing .env file
load_dotenv(ROOT / ".env")

BROKER = os.getenv("HIVEMQ_HOST")
USERNAME = os.getenv("HIVEMQ_USER")
PASSWORD = os.getenv("HIVEMQ_PASS")
PORT = 8883
TOPIC = "smartmeter/kaggle/data"

if not all([BROKER, USERNAME, PASSWORD]):
    raise SystemExit("Check HiveMQ credentials in your .env file.")

if not DATA_FILE.exists() or not MODEL_FILE.exists():
    raise SystemExit("Kaggle CSV or trained model file not found.")

model = joblib.load(MODEL_FILE)

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(USERNAME, PASSWORD)
client.tls_set(
    cert_reqs=ssl.CERT_REQUIRED,
    tls_version=ssl.PROTOCOL_TLS_CLIENT
)

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("Connected to HiveMQ Cloud.")
    else:
        print("Connection failed:", reason_code)

client.on_connect = on_connect
client.connect(BROKER, PORT, 60)
client.loop_start()
time.sleep(2)

print("Replaying Kaggle historical readings...")
print("Topic:", TOPIC)
print("Press Ctrl+C to stop.")

try:
    BUILDING_ID = 107
    for chunk in pd.read_csv(
        DATA_FILE,
        usecols=["building_id", "timestamp", "meter_reading", "anomaly"],
        chunksize=1000
    ):
        chunk = chunk.dropna(
            subset=["building_id", "timestamp", "meter_reading", "anomaly"]
        ).copy()
        chunk = chunk[chunk["building_id"] == BUILDING_ID]
        if chunk.empty:
            continue

        chunk["timestamp"] = pd.to_datetime(
            chunk["timestamp"], errors="coerce"
        )
        chunk = chunk.dropna(subset=["timestamp"])

        if chunk.empty:
            continue

        chunk["hour"] = chunk["timestamp"].dt.hour
        chunk["day_of_week"] = chunk["timestamp"].dt.dayofweek
        chunk["month"] = chunk["timestamp"].dt.month

        features = chunk[
            ["building_id", "meter_reading", "hour", "day_of_week", "month"]
        ]

        predictions = model.predict(features)

        for (_, row), prediction in zip(chunk.iterrows(), predictions):
            message = {
                "timestamp": row["timestamp"].isoformat(),
                "building_id": int(row["building_id"]),
                "meter_reading": float(row["meter_reading"]),
                "predicted_anomaly": int(prediction),
                "actual_anomaly": int(row["anomaly"]),
                "data_source": "Kaggle historical dataset"
            }

            info = client.publish(TOPIC, json.dumps(message), qos=1)
            info.wait_for_publish()

            print(json.dumps(message))
            time.sleep(1)

except KeyboardInterrupt:
    print("\nKaggle replay stopped.")

finally:
    client.loop_stop()
    client.disconnect()
