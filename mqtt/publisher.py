import paho.mqtt.client as mqtt
import ssl
import json
import random
import time
import os
from dotenv import load_dotenv
load_dotenv()


# HiveMQ Cloud details
BROKER = "50b0ba49257044d3b4b3faf5c7c09cd3.s1.eu.hivemq.cloud"
PORT = 8883

USERNAME = "smartmeter"
PASSWORD = os.getenv("HIVEMQ_PASSWORD")

TOPIC = "smartmeter/data"


# Create MQTT client
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

# Username and password
client.username_pw_set(USERNAME, PASSWORD)

# Enable TLS
client.tls_set(
    cert_reqs=ssl.CERT_REQUIRED,
    tls_version=ssl.PROTOCOL_TLS_CLIENT
)

# Connect to HiveMQ
client.connect(BROKER, PORT, 60)

print("Connected to HiveMQ Cloud!")
print("Sending smart meter data...")


try:
    while True:

        voltage = round(random.uniform(220, 240), 2)
        current = round(random.uniform(1, 5), 2)

        power = round(voltage * current, 2)

        data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "voltage": voltage,
            "current": current,
            "power": power,
            "energy": round(power / 1000, 3)
        }

        message = json.dumps(data)

        client.publish(TOPIC, message)

        print("Sent:", message)

        time.sleep(2)

except KeyboardInterrupt:
    print("\nPublisher stopped.")

finally:
    client.disconnect()