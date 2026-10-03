import json
import os

import numpy as np
import pandas as pd
import paho.mqtt.client as mqtt
from dotenv import load_dotenv
from sklearn.ensemble import IsolationForest

load_dotenv()

BROKER = os.getenv("HIVEMQ_HOST")
USERNAME = os.getenv("HIVEMQ_USER")
PASSWORD = os.getenv("HIVEMQ_PASS")
PORT = 8883

IN_TOPIC = "smartmeter/data"          # readings from publisher.py
RESULT_TOPIC = "smartmeter/result"    # every reading + Normal/Anomaly label
ANOMALY_TOPIC = "smartmeter/anomaly"  # only the anomalies

FEATURES = ["voltage", "current", "power", "energy"]

if not (BROKER and USERNAME and PASSWORD):
    raise SystemExit("Missing HIVEMQ_HOST / HIVEMQ_USER / HIVEMQ_PASS in .env")


def train_model():
    """Isolation Forest trained on synthetic 'normal' smart meter readings."""
    rng = np.random.default_rng(42)
    n = 2000
    voltage = rng.uniform(220, 240, n)
    current = rng.uniform(1, 5, n)
    power = voltage * current
    X = pd.DataFrame(
        {"voltage": voltage, "current": current, "power": power, "energy": power / 1000}
    )
    model = IsolationForest(n_estimators=100, contamination=0.02, random_state=42)
    model.fit(X[FEATURES])
    return model


model = train_model()
print("AI model trained.")


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("Connected to HiveMQ Cloud! Listening on", IN_TOPIC)
        client.subscribe(IN_TOPIC)
    else:
        print("Connection failed:", reason_code)


def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        row = pd.DataFrame([[float(data[k]) for k in FEATURES]], columns=FEATURES)
    except Exception:
        return  # ignore malformed messages

    pred = model.predict(row)[0]
    score = float(model.decision_function(row)[0])
    status = "Anomaly" if pred == -1 else "Normal"

    result = dict(data)
    result["ai_status"] = status
    result["score"] = round(score, 4)
    payload = json.dumps(result)

    client.publish(RESULT_TOPIC, payload)
    if status == "Anomaly":
        client.publish(ANOMALY_TOPIC, payload, retain=True)
        print("ANOMALY :", payload)
    else:
        print("Normal  :", data.get("timestamp"), data.get("power"), "W")


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