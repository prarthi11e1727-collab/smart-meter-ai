import json
import os
from pathlib import Path

import joblib
import pandas as pd
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

BROKER = os.getenv("HIVEMQ_HOST")
USERNAME = os.getenv("HIVEMQ_USER")
PASSWORD = os.getenv("HIVEMQ_PASS")
PORT = 8883

IN_TOPIC = "smartmeter/kaggle/data"
RESULT_TOPIC = "smartmeter/kaggle/result"
ANOMALY_TOPIC = "smartmeter/kaggle/anomaly"

MODEL_FILE = ROOT / "ai" / "kaggle_anomaly_model.joblib"
FEATURES = ["building_id", "meter_reading", "hour", "day_of_week", "month"]
THRESHOLD = 0.5   # lower it (for example 0.3) to catch more anomalies

if not (BROKER and USERNAME and PASSWORD):
    raise SystemExit("Missing HIVEMQ_HOST / HIVEMQ_USER / HIVEMQ_PASS in .env")
if not MODEL_FILE.exists():
    raise SystemExit("Model file not found. Run ai/kaggle_anomaly_detection.py first.")

model = joblib.load(MODEL_FILE)
ANOMALY_COL = list(model.classes_).index(1)
print("Kaggle AI model loaded.")


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("Connected to HiveMQ Cloud! Listening on", IN_TOPIC)
        client.subscribe(IN_TOPIC)
    else:
        print("Connection failed:", reason_code)


def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        ts = pd.to_datetime(data["timestamp"])
        row = pd.DataFrame(
            [[
                int(data["building_id"]),
                float(data["meter_reading"]),
                ts.hour,
                ts.dayofweek,
                ts.month,
            ]],
            columns=FEATURES,
        )
    except Exception as e:
        print("Skipped bad message:", e)
        return

    probability = float(model.predict_proba(row)[0][ANOMALY_COL])
    status = "Anomaly" if probability >= THRESHOLD else "Normal"

    result = dict(data)
    result["ai_status"] = status
    result["anomaly_probability"] = round(probability, 4)
    payload = json.dumps(result)

    client.publish(RESULT_TOPIC, payload)
    if status == "Anomaly":
        client.publish(ANOMALY_TOPIC, payload)
        print("ANOMALY :", data["timestamp"], data["meter_reading"], "| chance", round(probability, 2))
    else:
        print("Normal  :", data["timestamp"], data["meter_reading"])


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(USERNAME, PASSWORD)
client.tls_set()
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, 60)
try:
    client.loop_forever()
except KeyboardInterrupt:
    print("\nDetector stopped.")
    client.disconnect()