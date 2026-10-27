
import json
import queue
import streamlit as st
import pandas as pd
import plotly.express as px
import paho.mqtt.client as mqtt
from streamlit_autorefresh import st_autorefresh

TOPIC = "smartmeter/kaggle/data"

@st.cache_resource
def start_mqtt():
    q = queue.Queue()
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    c.username_pw_set(
        st.secrets["HIVEMQ_USER"],
        st.secrets["HIVEMQ_PASS"]
    )
    c.tls_set()

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            client.subscribe(TOPIC)
        else:
            print("MQTT connection failed:", reason_code)

    def on_message(client, userdata, msg):
        try:
            q.put(json.loads(msg.payload.decode()))
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    c.on_connect = on_connect
    c.on_message = on_message
    c.connect(st.secrets["HIVEMQ_HOST"], 8883, 60)
    c.loop_start()
    return q

q = start_mqtt()
st_autorefresh(interval=2000, key="mqtt_refresh")

if "readings" not in st.session_state:
    st.session_state.readings = []

while not q.empty():
    st.session_state.readings.append(q.get())

# Keep recent readings in memory
st.session_state.readings = st.session_state.readings[-500:]

st.title("AI-Based Smart Meter Consumption Anomaly Detection")
st.caption("Kaggle historical readings streamed through HiveMQ Cloud")

if st.session_state.readings:
    df = pd.DataFrame(st.session_state.readings)

    if "meter_reading" in df.columns:
        df["meter_reading"] = pd.to_numeric(
            df["meter_reading"], errors="coerce"
        )

    if "predicted_anomaly" in df.columns:
        df["predicted_anomaly"] = pd.to_numeric(
            df["predicted_anomaly"], errors="coerce"
        )

    total = len(df)
    anomalies = (
        int((df["predicted_anomaly"] == 1).sum())
        if "predicted_anomaly" in df.columns else 0
    )
    latest = (
        df["meter_reading"].dropna().iloc[-1]
        if "meter_reading" in df.columns
        and df["meter_reading"].notna().any()
        else None
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Readings Received", total)
    col2.metric("AI-Detected Anomalies", anomalies)
    col3.metric(
        "Latest Consumption",
        f"{latest:.2f}" if latest is not None else "N/A"
    )

    if {"timestamp", "meter_reading"}.issubset(df.columns):
        chart_df = df.copy()
        chart_df["timestamp"] = pd.to_datetime(
            chart_df["timestamp"], errors="coerce"
        )
        chart_df = chart_df.dropna(
            subset=["timestamp", "meter_reading"]
        )

        if not chart_df.empty:
            st.subheader("Electricity Consumption")
            st.line_chart(
                chart_df.set_index("timestamp")["meter_reading"]
            )

    if {"meter_reading", "predicted_anomaly"}.issubset(df.columns):
        st.subheader("AI Anomaly Detection")
        anomaly_df = df.copy()
        anomaly_df["AI Status"] = anomaly_df[
            "predicted_anomaly"
        ].map({0: "Normal", 1: "Anomaly"})

        st.dataframe(
            anomaly_df[
                [c for c in [
                    "timestamp", "building_id", "meter_reading",
                    "AI Status", "actual_anomaly"
                ] if c in anomaly_df.columns]
            ].tail(20),
            use_container_width=True
        )

    st.subheader("Latest MQTT Readings")
    st.dataframe(df.tail(20), use_container_width=True)

else:
    st.info("Waiting for Kaggle readings from HiveMQ Cloud...")
    st.write("Start `mqtt/kaggle_publisher.py` on your computer.")
