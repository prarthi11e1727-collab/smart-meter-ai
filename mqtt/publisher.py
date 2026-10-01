import paho.mqtt.client as mqtt
import ssl
import json
import random
import time

BROKER = "50b0ba49257044d3b4b3faf5c7c09cd3.s1.eu.hivemq.cloud"
PORT = 8883

USERNAME = "smartmeter"
PASSWORD = "12345678"

TOPIC = "smartmeter/data"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

client.username_pw_set(USERNAME, PASSWORD)

client.tls_set(
    cert_reqs=ssl.CERT_REQUIRED,
    tls_version=ssl.PROTOCOL_TLS_CLIENT
)

client.connect(BROKER, PORT, 60)

# IMPORTANT: start MQTT network loop
client.loop_start()

print("Connected to HiveMQ Cloud!")
print("Sending smart meter data...")

try:
    while True:

        voltage = round(random.uniform(220, 240), 2)
        current = round(random.uniform(1, 5), 2)
        power = round(voltage * current, 2)
        energy = round(power / 1000, 3)

        data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "voltage": voltage,
            "current": current,
            "power": power,
            "energy": energy
        }

        message = json.dumps(data)

        info = client.publish(TOPIC, message)

        print("Sent:", message)

        time.sleep(2)

except KeyboardInterrupt:
    print("\nPublisher stopped.")

finally:
    client.loop_stop()
    client.disconnect()