import streamlit as st
import pandas as pd
import paho.mqtt.client as mqtt
import ssl
import json
import threading

st.set_page_config(
    page_title="Smart Meter AI",
    page_icon="⚡",
    layout="wide"
)


@st.cache_resource
def start_mqtt():

    state = {
        "latest": None,
        "history": [],
        "lock": threading.Lock()
    }

    def on_connect(client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            print("Connected to HiveMQ Cloud")
            print("SUBSCRIBING TO:", st.secrets["MQTT_TOPIC"])
            client.subscribe(st.secrets["MQTT_TOPIC"])
        else:
            print("MQTT connection failed:", reason_code)

    def on_message(client, userdata, msg):

        try:
            data = json.loads(msg.payload.decode())

            with state["lock"]:
                state["latest"] = data
                state["history"].append(data)

                if len(state["history"]) > 100:
                    state["history"].pop(0)

        except Exception as e:
            print("Message error:", e)

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2
    )

    client.username_pw_set(
        st.secrets["MQTT_USERNAME"],
        st.secrets["MQTT_PASSWORD"]
    )

    client.tls_set(
        cert_reqs=ssl.CERT_REQUIRED,
        tls_version=ssl.PROTOCOL_TLS_CLIENT
    )

    client.on_connect = on_connect
    client.on_message = on_message

    try:
    client.connect(
        st.secrets["MQTT_BROKER"],
        int(st.secrets["MQTT_PORT"]),
        60
    )
except Exception as e:
    print("MQTT CONNECTION ERROR:", repr(e))

    client.loop_start()

    return state


# Start MQTT
state = start_mqtt()


# Get latest data
with state["lock"]:
    latest = state["latest"]
    history = list(state["history"])


st.title("⚡ AI-Based Smart Meter Monitoring")
st.subheader("Live IoT Electricity Consumption Dashboard")


if latest:

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Voltage",
        f"{float(latest['voltage']):.2f} V"
    )

    col2.metric(
        "Current",
        f"{float(latest['current']):.2f} A"
    )

    col3.metric(
        "Power",
        f"{float(latest['power']):.2f} W"
    )

    col4.metric(
        "Energy / Interval",
        f"{float(latest['energy']):.3f}"
    )

    st.success("🟢 Connected — Live MQTT data received")

    st.divider()

    if history:

        df = pd.DataFrame(history)

        st.subheader("📈 Live Power Consumption")
        st.line_chart(df["power"])

        st.subheader("⚡ Live Voltage")
        st.line_chart(df["voltage"])

        st.subheader("🔌 Live Current")
        st.line_chart(df["current"])

        st.subheader("📋 Recent Meter Readings")
        st.dataframe(
            df.tail(20),
            width="stretch"
        )

else:

    st.warning("⏳ Waiting for live data from HiveMQ Cloud...")

    st.info(
        "Make sure your Python MQTT publisher is running."
    )