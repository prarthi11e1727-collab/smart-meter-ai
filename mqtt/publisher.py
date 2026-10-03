import json
import os
import random
import ssl
import time

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

# Load HIVEMQ_HOST, HIVEMQ_USER, HIVEMQ_PASS from the .env file
load_dotenv()

BROKER = os.getenv("HIVEMQ_HOST")
USERNAME = os.getenv("HIVEMQ_USER")
PASSWORD = os.getenv("HIVEMQ_PASS")
PORT = 8883
TOPIC = "smartmeter/data"

if not (BROKER and USERNAME and PASSWORD):
    raise SystemExit("Missing HIVEMQ_HOST / HIVEMQ_USER / HIVEMQ_PASS in .env")


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("Connected to HiveMQ Cloud!")
    else:
        print("Connection failed:", reason_code)


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(USERNAME, PASSWORD)
client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS_CLIENT)
client.on_connect = on_connect

client.connect(BROKER, PORT, 60)
client.loop_start()

time.sleep(2)  # give the connection a moment before sending
print("Sending smart meter data...")

try:
    while True:
        if random.random() < 0.08:  # occasional fault for the demo
            voltage = round(random.uniform(255, 275), 2)
            current = round(random.uniform(7, 10), 2)
        else:
            voltage = round(random.uniform(220, 240), 2)
            current = round(random.uniform(1, 5), 2)

        power = round(voltage * current, 2)
        energy = round(power / 1000, 3)

        data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "voltage": voltage,
            "current": current,
            "power": power,
            "energy": energy,
        }

        message = json.dumps(data)
        client.publish(TOPIC, message)
        print("Sent:", message)

        time.sleep(2)

except KeyboardInterrupt:
    print("\nPublisher stopped.")

finally:
    client.loop_stop()
    client.disconnect()