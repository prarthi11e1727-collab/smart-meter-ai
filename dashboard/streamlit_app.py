import hmac
import json
import os
import queue

import numpy as np
import pandas as pd
import paho.mqtt.client as mqtt
import streamlit as st
from sklearn.ensemble import IsolationForest
from streamlit_autorefresh import st_autorefresh

try:  # optional: lets you use a local .env when running on your PC
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ---------------------------------------------------------------- settings
TOPIC = "smartmeter/data"          # must match publisher.py
PORT = 8883                        # HiveMQ Cloud TLS port
HIGH_POWER_LIMIT = 1000            # W, fixed threshold alert
MAX_ROWS = 500                     # readings kept in memory
REFRESH_MS = 2000                  # dashboard refresh interval
FEATURES = ["voltage", "current", "power", "energy"]

st.set_page_config(page_title="Smart Meter Monitoring", page_icon="⚡", layout="wide")


def get_secret(name):
    """Read from Streamlit secrets (cloud) or environment / .env (local)."""
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.getenv(name)


# ---------------------------------------------------------------- LOGIN
def check_login(username, password):
    valid_user = get_secret("APP_USERNAME")
    valid_pass = get_secret("APP_PASSWORD")
    if not valid_user or not valid_pass:
        return None  # login not configured
    ok_user = hmac.compare_digest(username.encode(), str(valid_user).encode())
    ok_pass = hmac.compare_digest(password.encode(), str(valid_pass).encode())
    return ok_user and ok_pass


if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    left, middle, right = st.columns([1, 1.2, 1])
    with middle:
        st.title("⚡ Smart Meter Login")
        st.caption("AI-Based Smart Meter Consumption Anomaly Detection")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)
        if submitted:
            result = check_login(username, password)
            if result is None:
                st.error("Login is not configured. Add APP_USERNAME and APP_PASSWORD in Secrets.")
            elif result:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Login failed: wrong username or password.")
    st.stop()  # nothing below runs until the user is logged in

# Sidebar logout
with st.sidebar:
    st.write("Logged in")
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()


# ---------------------------------------------------------------- AI model
@st.cache_resource
def load_model():
    """Isolation Forest trained on synthetic 'normal' smart meter readings."""
    rng = np.random.default_rng(42)
    n = 2000
    voltage = rng.uniform(220, 240, n)
    current = rng.uniform(1, 5, n)
    power = voltage * current
    energy = power / 1000
    X = pd.DataFrame(
        {"voltage": voltage, "current": current, "power": power, "energy": energy}
    )
    model = IsolationForest(n_estimators=100, contamination=0.02, random_state=42)
    model.fit(X[FEATURES])
    return model


model = load_model()


# ---------------------------------------------------------------- MQTT
@st.cache_resource
def start_mqtt():
    """Start the MQTT client once; messages arrive through a thread-safe queue."""
    q = queue.Queue()
    status = {"connected": False, "error": None}

    host = get_secret("HIVEMQ_HOST")
    user = get_secret("HIVEMQ_USER")
    password = get_secret("HIVEMQ_PASS")

    if not (host and user and password):
        status["error"] = "Missing HIVEMQ_HOST / HIVEMQ_USER / HIVEMQ_PASS in secrets."
        return q, status, None

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(user, password)
    client.tls_set()

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            status["connected"] = True
            status["error"] = None
            client.subscribe(TOPIC)
        else:
            status["connected"] = False
            status["error"] = f"Connection refused: {reason_code}"

    def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
        status["connected"] = False

    def on_message(client, userdata, msg):
        try:
            q.put(json.loads(msg.payload.decode()))
        except Exception:
            pass  # ignore malformed messages

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    try:
        client.connect(host, PORT, 60)
        client.loop_start()
    except Exception as e:
        status["error"] = str(e)

    return q, status, client


q, mqtt_status, _client = start_mqtt()

# Re-run the script automatically so new readings show up
st_autorefresh(interval=REFRESH_MS, key="live_refresh")

# ---------------------------------------------------------------- state
if "readings" not in st.session_state:
    st.session_state.readings = []
if "anomaly_log" not in st.session_state:
    st.session_state.anomaly_log = []

# Drain new messages, classify each one
while not q.empty():
    r = q.get()
    try:
        row = {k: float(r[k]) for k in FEATURES}
    except (KeyError, TypeError, ValueError):
        continue
    row["timestamp"] = r.get("timestamp", pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"))
    pred = model.predict(pd.DataFrame([row])[FEATURES])[0]
    row["ai_status"] = "Anomaly" if pred == -1 else "Normal"
    row["high_power"] = row["power"] > HIGH_POWER_LIMIT
    st.session_state.readings.append(row)
    if row["ai_status"] == "Anomaly":
        st.session_state.anomaly_log.append(row)

st.session_state.readings = st.session_state.readings[-MAX_ROWS:]
st.session_state.anomaly_log = st.session_state.anomaly_log[-100:]

df = pd.DataFrame(st.session_state.readings)

# ---------------------------------------------------------------- UI
st.title("⚡ AI-Based Smart Meter Monitoring")

if mqtt_status["error"]:
    st.error(f"MQTT problem: {mqtt_status['error']}")
elif mqtt_status["connected"]:
    st.success(f"Connected to HiveMQ Cloud — topic: {TOPIC}")
else:
    st.warning("Connecting to HiveMQ Cloud...")

if df.empty:
    st.info("Waiting for live data from HiveMQ Cloud (is publisher.py running?)")
    st.stop()

latest = df.iloc[-1]

# Alerts
if latest["high_power"]:
    st.error(f"🚨 High Power Alert: {latest['power']:.1f} W (limit {HIGH_POWER_LIMIT} W)")
if latest["ai_status"] == "Anomaly":
    st.error("🤖 AI Anomaly Alert: unusual consumption pattern detected")

# Metrics
c1, c2, c3, c4 = st.columns(4)
c1.metric("Latest Power (W)", f"{latest['power']:.1f}")
c2.metric("Voltage (V)", f"{latest['voltage']:.1f}")
c3.metric("Current (A)", f"{latest['current']:.2f}")
c4.metric("Energy (kWh)", f"{latest['energy']:.3f}")

c5, c6, c7, c8 = st.columns(4)
c5.metric("Maximum Power (W)", f"{df['power'].max():.1f}")
c6.metric("Average Power (W)", f"{df['power'].mean():.1f}")
c7.metric("AI Anomaly Status", latest["ai_status"])
c8.metric("AI Anomaly Count", int((df["ai_status"] == "Anomaly").sum()))

st.caption(f"System status: Online | Last reading: {latest['timestamp']}")

# Charts
chart_df = df.set_index("timestamp")
g1, g2, g3 = st.columns(3)
with g1:
    st.subheader("Power (W)")
    st.line_chart(chart_df["power"])
with g2:
    st.subheader("Voltage (V)")
    st.line_chart(chart_df["voltage"])
with g3:
    st.subheader("Current (A)")
    st.line_chart(chart_df["current"])

# Tables
t1, t2 = st.columns(2)
with t1:
    st.subheader("Recent Smart Meter Readings")
    st.dataframe(
        df.tail(20).iloc[::-1][["timestamp"] + FEATURES + ["ai_status"]],
        use_container_width=True,
        hide_index=True,
    )
with t2:
    st.subheader("AI Anomaly Log")
    if st.session_state.anomaly_log:
        log_df = pd.DataFrame(st.session_state.anomaly_log).iloc[::-1]
        st.dataframe(
            log_df[["timestamp"] + FEATURES],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.write("No anomalies detected yet.")

st.subheader("High Power Alerts")
hp = df[df["high_power"]].tail(10).iloc[::-1]
if hp.empty:
    st.write(f"No readings above {HIGH_POWER_LIMIT} W.")
else:
    st.dataframe(
        hp[["timestamp", "power"]], use_container_width=True, hide_index=True
    )