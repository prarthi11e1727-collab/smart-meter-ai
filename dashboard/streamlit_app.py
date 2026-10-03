import hmac
import json
import os
import queue

import altair as alt
import numpy as np
import pandas as pd
import paho.mqtt.client as mqtt
import streamlit as st
from sklearn.ensemble import IsolationForest
from streamlit_autorefresh import st_autorefresh

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ---------------------------------------------------------------- settings
TOPIC = "smartmeter/result"   # AI-labelled readings published by live_anomaly.py
PORT = 8883
MAX_ROWS = 500
REFRESH_MS = 2000
FEATURES = ["voltage", "current", "power", "energy"]
PAGES = [
    "🏠  Overview",
    "📈  Live Charts",
    "🚨  Alerts",
    "🤖  AI Anomalies",
    "🗂️  Data & Export",
    "ℹ️  About",
]

st.set_page_config(page_title="Smart Meter Monitoring", page_icon="⚡", layout="wide")

CSS = """
<style>
.block-container {padding-top: 2rem; padding-bottom: 3rem; max-width: 1300px;}
[data-testid="stMetric"] {
    background: linear-gradient(135deg, #1e293b, #0f172a);
    border: 1px solid #334155; border-radius: 14px;
    padding: 16px 18px; box-shadow: 0 2px 8px rgba(0,0,0,.25);
}
[data-testid="stMetricLabel"] {color: #94a3b8;}
.hero {background: linear-gradient(90deg, #f59e0b, #ef4444);
       padding: 22px 28px; border-radius: 16px; margin-bottom: 22px;}
.hero h1 {margin: 0; color: #fff; font-size: 2rem;}
.hero p {margin: 4px 0 0; color: #fff; opacity: .9;}
.pill {display: inline-block; padding: 4px 14px; border-radius: 999px;
       font-size: .85rem; font-weight: 600; margin-bottom: 14px;}
.pill-ok {background: #064e3b; color: #6ee7b7;}
.pill-warn {background: #78350f; color: #fcd34d;}
.pill-bad {background: #7f1d1d; color: #fca5a5;}
.stButton > button, .stDownloadButton > button {
    border-radius: 10px; font-weight: 600; padding: .5rem 1rem;}
footer {visibility: hidden;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def hero(title, subtitle):
    st.markdown(
        f'<div class="hero"><h1>{title}</h1><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )


def get_secret(name):
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
        return None
    ok_user = hmac.compare_digest(username.encode(), str(valid_user).encode())
    ok_pass = hmac.compare_digest(password.encode(), str(valid_pass).encode())
    return ok_user and ok_pass


if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    _, middle, _ = st.columns([1, 1.3, 1])
    with middle:
        hero("⚡ Smart Meter Login", "AI-Based Consumption Anomaly Detection")
        with st.form("login_form"):
            username = st.text_input("👤 Username")
            password = st.text_input("🔒 Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True, type="primary")
        if submitted:
            result = check_login(username, password)
            if result is None:
                st.error("Login is not configured. Add APP_USERNAME and APP_PASSWORD in Secrets.")
            elif result:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Login failed: wrong username or password.")
    st.stop()


# ---------------------------------------------------------------- AI model
@st.cache_resource
def load_model():
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


model = load_model()


# ---------------------------------------------------------------- MQTT
@st.cache_resource
def start_mqtt():
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
            pass

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
st_autorefresh(interval=REFRESH_MS, key="live_refresh")

# ---------------------------------------------------------------- state
if "readings" not in st.session_state:
    st.session_state.readings = []
if "anomaly_log" not in st.session_state:
    st.session_state.anomaly_log = []

while not q.empty():
    r = q.get()
    try:
        row = {k: float(r[k]) for k in FEATURES}
    except (KeyError, TypeError, ValueError):
        continue
    row["timestamp"] = r.get("timestamp", pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"))
    status = r.get("ai_status")  # label sent by live_anomaly.py
    if status not in ("Normal", "Anomaly"):  # fallback: classify locally
        pred = model.predict(pd.DataFrame([row])[FEATURES])[0]
        status = "Anomaly" if pred == -1 else "Normal"
    row["ai_status"] = status
    st.session_state.readings.append(row)
    if row["ai_status"] == "Anomaly":
        st.session_state.anomaly_log.append(row)

st.session_state.readings = st.session_state.readings[-MAX_ROWS:]
st.session_state.anomaly_log = st.session_state.anomaly_log[-100:]

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("## ⚡ Smart Meter")
    st.caption("AI Anomaly Detection · IoT")
    page = st.radio("Navigation", PAGES, label_visibility="collapsed")
    st.divider()
    limit = st.slider("🚨 High power limit (W)", 500, 1200, 1000, step=50)
    if st.button("🗑️ Clear data", use_container_width=True):
        st.session_state.readings = []
        st.session_state.anomaly_log = []
        st.rerun()
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

df = pd.DataFrame(st.session_state.readings)
if not df.empty:
    df["high_power"] = df["power"] > limit

# connection badge
if mqtt_status["error"]:
    st.markdown(f'<span class="pill pill-bad">❌ {mqtt_status["error"]}</span>', unsafe_allow_html=True)
elif mqtt_status["connected"]:
    st.markdown(f'<span class="pill pill-ok">🟢 Connected · {TOPIC}</span>', unsafe_allow_html=True)
else:
    st.markdown('<span class="pill pill-warn">🟡 Connecting to HiveMQ Cloud...</span>', unsafe_allow_html=True)


# ---------------------------------------------------------------- charts
def make_chart(data, col, title, unit, color, normal=None, rule=None, height=380):
    """Readable line chart: zoomed axis, labels, markers, tooltip, optional
    green 'normal range' band and red limit line."""
    d = data.copy()
    d["time"] = pd.to_datetime(d["timestamp"])
    lo, hi = float(d[col].min()), float(d[col].max())
    pad = max((hi - lo) * 0.15, 0.5)
    ymin, ymax = lo - pad, hi + pad
    if normal:
        ymin, ymax = min(ymin, normal[0] - 2), max(ymax, normal[1] + 2)
    if rule:
        ymax = max(ymax, rule + 20)
    ydomain = alt.Scale(domain=[ymin, ymax], nice=False)

    base = alt.Chart(d).encode(
        x=alt.X("time:T", title="Time",
                axis=alt.Axis(format="%H:%M:%S", labelAngle=0, tickCount=6, grid=False)),
        y=alt.Y(f"{col}:Q", title=f"{title} ({unit})", scale=ydomain),
        tooltip=[
            alt.Tooltip("time:T", title="Time", format="%H:%M:%S"),
            alt.Tooltip(f"{col}:Q", title=f"{title} ({unit})", format=".2f"),
        ],
    )
    layers = []
    if normal:
        band_df = pd.DataFrame({"lo": [normal[0]], "hi": [normal[1]]})
        layers.append(
            alt.Chart(band_df).mark_rect(color="#22c55e", opacity=0.12).encode(
                y=alt.Y("lo:Q", scale=ydomain), y2="hi:Q"
            )
        )
    if rule:
        layers.append(
            alt.Chart(pd.DataFrame({"r": [rule]}))
            .mark_rule(color="#ef4444", strokeDash=[6, 4], strokeWidth=2)
            .encode(y=alt.Y("r:Q", scale=ydomain))
        )
    layers.append(base.mark_line(color=color, strokeWidth=2.5, interpolate="monotone"))
    layers.append(base.mark_point(color=color, size=45, filled=True))
    return alt.layer(*layers).properties(height=height).interactive()


# ---------------------------------------------------------------- pages
def page_overview():
    hero("⚡ Smart Meter Dashboard", "Live electricity monitoring with AI anomaly detection")
    latest = df.iloc[-1]
    if latest["high_power"]:
        st.error(f"🚨 High Power Alert: {latest['power']:.1f} W (limit {limit} W)")
    if latest["ai_status"] == "Anomaly":
        st.error("🤖 AI Anomaly Alert: unusual consumption pattern detected")

    c1, c2, c3, c4 = st.columns(4, gap="medium")
    c1.metric("⚡ Latest Power (W)", f"{latest['power']:.1f}")
    c2.metric("🔌 Voltage (V)", f"{latest['voltage']:.1f}")
    c3.metric("〰️ Current (A)", f"{latest['current']:.2f}")
    c4.metric("🔋 Energy (kWh)", f"{latest['energy']:.3f}")
    st.write("")
    c5, c6, c7, c8 = st.columns(4, gap="medium")
    c5.metric("📈 Max Power (W)", f"{df['power'].max():.1f}")
    c6.metric("📊 Avg Power (W)", f"{df['power'].mean():.1f}")
    c7.metric("🤖 AI Status", latest["ai_status"])
    c8.metric("⚠️ Anomaly Count", int((df["ai_status"] == "Anomaly").sum()))
    st.caption(f"System status: Online · Last reading: {latest['timestamp']}")
    st.write("")
    st.subheader("Power trend")
    st.caption(f"Red dashed line = high power limit ({limit} W)")
    st.altair_chart(
        make_chart(df.tail(60), "power", "Power", "W", "#f59e0b", rule=limit, height=300),
        use_container_width=True,
    )


def page_charts():
    hero("📈 Live Charts", "Real-time voltage, current and power graphs")
    n = st.slider("Readings to show", 10, 200, 60, step=10)
    view = df.tail(n)

    def stats(col, unit, fmt):
        a, b, c = st.columns(3, gap="medium")
        a.metric("⬇️ Min", f"{view[col].min():{fmt}} {unit}")
        b.metric("📊 Average", f"{view[col].mean():{fmt}} {unit}")
        c.metric("⬆️ Max", f"{view[col].max():{fmt}} {unit}")
        st.write("")

    t1, t2, t3 = st.tabs(["⚡ Power", "🔌 Voltage", "〰️ Current"])
    with t1:
        stats("power", "W", ".1f")
        st.caption(f"Red dashed line = high power limit ({limit} W). Hover over a point for exact values.")
        st.altair_chart(
            make_chart(view, "power", "Power", "W", "#f59e0b", rule=limit),
            use_container_width=True,
        )
    with t2:
        stats("voltage", "V", ".1f")
        st.caption("Green band = normal voltage range (220 to 240 V). Hover over a point for exact values.")
        st.altair_chart(
            make_chart(view, "voltage", "Voltage", "V", "#38bdf8", normal=(220, 240)),
            use_container_width=True,
        )
    with t3:
        stats("current", "A", ".2f")
        st.caption("Green band = normal current range (1 to 5 A). Hover over a point for exact values.")
        st.altair_chart(
            make_chart(view, "current", "Current", "A", "#a78bfa", normal=(1, 5)),
            use_container_width=True,
        )


def page_alerts():
    hero("🚨 Alerts", f"Readings above the {limit} W limit")
    hp = df[df["high_power"]]
    c1, c2, c3 = st.columns(3, gap="medium")
    c1.metric("🚨 Alerts", len(hp))
    c2.metric("📉 Share of readings", f"{100 * len(hp) / len(df):.0f}%")
    c3.metric("🔝 Highest alert (W)", f"{hp['power'].max():.1f}" if len(hp) else "-")
    st.write("")
    if hp.empty:
        st.success(f"✅ No readings above {limit} W.")
    else:
        st.dataframe(
            hp.tail(30).iloc[::-1][["timestamp", "voltage", "current", "power"]],
            use_container_width=True, hide_index=True,
        )


def page_anomalies():
    hero("🤖 AI Anomalies", "Isolation Forest flags unusual consumption patterns")
    n_anom = int((df["ai_status"] == "Anomaly").sum())
    c1, c2, c3 = st.columns(3, gap="medium")
    c1.metric("🤖 Anomalies", n_anom)
    c2.metric("✅ Normal readings", len(df) - n_anom)
    c3.metric("📉 Anomaly rate", f"{100 * n_anom / len(df):.1f}%")
    st.write("")
    left, right = st.columns(2, gap="large")
    with left:
        st.subheader("Voltage vs Power")
        st.scatter_chart(df, x="voltage", y="power", color="ai_status", height=320)
    with right:
        st.subheader("Anomaly log")
        if st.session_state.anomaly_log:
            log_df = pd.DataFrame(st.session_state.anomaly_log).iloc[::-1]
            st.dataframe(log_df[["timestamp"] + FEATURES], use_container_width=True, hide_index=True)
        else:
            st.info("No anomalies detected yet.")


def page_data():
    hero("🗂️ Data & Export", "Recent readings received from the smart meter")
    shown = df.iloc[::-1][["timestamp"] + FEATURES + ["ai_status"]]
    st.dataframe(shown.head(100), use_container_width=True, hide_index=True)
    st.download_button(
        "⬇️ Download CSV", shown.to_csv(index=False),
        file_name="smart_meter_data.csv", mime="text/csv", type="primary",
    )


def page_about():
    hero("ℹ️ About", "AI-Based Smart Meter Consumption Anomaly Detection Using IoT")
    st.markdown(
        """
**How it works**

`Data generator → MQTT → HiveMQ Cloud → AI model → Dashboard → Alerts`

- 📡 **MQTT + HiveMQ Cloud** carry the live voltage, current, power and energy readings.
- 🤖 **Isolation Forest** (scikit-learn) classifies every reading as Normal or Anomaly.
- 🚨 **High power alert** fires when power goes above the limit you set in the sidebar.
- 🧩 **Node-RED** provides the second, local dashboard.

**Tech stack:** Python · Streamlit · paho-mqtt · scikit-learn · Node-RED · SQLite
        """
    )


# ---------------------------------------------------------------- router
if page.endswith("About"):
    page_about()
elif df.empty:
    hero("⚡ Smart Meter Dashboard", "Waiting for the first reading")
    st.info("Waiting for live data from HiveMQ Cloud. Are publisher.py and live_anomaly.py running?")
elif page.endswith("Overview"):
    page_overview()
elif page.endswith("Live Charts"):
    page_charts()
elif page.endswith("Alerts"):
    page_alerts()
elif page.endswith("AI Anomalies"):
    page_anomalies()
elif page.endswith("Data & Export"):
    page_data()