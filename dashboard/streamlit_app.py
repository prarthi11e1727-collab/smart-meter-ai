import hmac
import json
import os
import queue

import altair as alt
import pandas as pd
import paho.mqtt.client as mqtt
import streamlit as st
from streamlit_autorefresh import st_autorefresh

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ---------------------------------------------------------------- settings
TOPIC = "smartmeter/kaggle/result"   # AI-labelled readings from kaggle_live_anomaly.py
PORT = 8883
MAX_ROWS = 500
REFRESH_MS = 2000
AI_THRESHOLD = 0.5   # same value as THRESHOLD in kaggle_live_anomaly.py
PAGES = [
    "🏠  Overview",
    "📈  Live Charts",
    "🚨  Alerts",
    "🤖  AI Anomalies",
    "🗂️  Data & Export",
    "ℹ️  About",
]
STATUS_COLORS = alt.Scale(domain=["Normal", "Anomaly"], range=["#38bdf8", "#ef4444"])

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
if "seen" not in st.session_state:
    st.session_state.seen = set()

while not q.empty():
    r = q.get()
    try:
        row = {
            "timestamp": str(r["timestamp"]),
            "building_id": int(r["building_id"]),
            "meter_reading": float(r["meter_reading"]),
        }
        ai_status = r["ai_status"]
        if ai_status not in ("Normal", "Anomaly"):
            continue
        row["ai_status"] = ai_status
        row["anomaly_probability"] = float(r.get("anomaly_probability", float("nan")))
        row["actual_anomaly"] = (
            float(r["actual_anomaly"]) if "actual_anomaly" in r else float("nan")
        )
    except (KeyError, TypeError, ValueError):
        continue
    key = (row["timestamp"], row["building_id"])
    if key in st.session_state.seen:   # skip repeated messages
        continue
    st.session_state.seen.add(key)
    st.session_state.readings.append(row)
    if ai_status == "Anomaly":
        st.session_state.anomaly_log.append(row)

st.session_state.readings = st.session_state.readings[-MAX_ROWS:]
st.session_state.anomaly_log = st.session_state.anomaly_log[-100:]

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("## ⚡ Smart Meter")
    st.caption("AI Anomaly Detection · IoT")
    page = st.radio("Navigation", PAGES, label_visibility="collapsed")
    st.divider()
    limit = st.number_input("🚨 High reading limit (kWh)", min_value=0.0, value=500.0, step=10.0)
    if st.button("🗑️ Clear data", use_container_width=True):
        st.session_state.readings = []
        st.session_state.anomaly_log = []
        st.session_state.seen = set()
        st.rerun()
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

df = pd.DataFrame(st.session_state.readings)
if not df.empty:
    df["high_reading"] = df["meter_reading"] > limit

# connection badge
if mqtt_status["error"]:
    st.markdown(f'<span class="pill pill-bad">❌ {mqtt_status["error"]}</span>', unsafe_allow_html=True)
elif mqtt_status["connected"]:
    st.markdown(f'<span class="pill pill-ok">🟢 Connected · {TOPIC}</span>', unsafe_allow_html=True)
else:
    st.markdown('<span class="pill pill-warn">🟡 Connecting to HiveMQ Cloud...</span>', unsafe_allow_html=True)


# ---------------------------------------------------------------- charts
def make_chart(data, col, title, unit, color, rule=None, height=380,
               mark_status=False, domain=None):
    """Line chart with zoomed axis, tooltip, optional red limit line,
    and optional red/blue points for Anomaly/Normal."""
    d = data.copy()
    d["time"] = pd.to_datetime(d["timestamp"])
    lo, hi = float(d[col].min()), float(d[col].max())
    if domain:
        ymin, ymax = domain
        show_rule = rule is not None
    else:
        pad = max((hi - lo) * 0.15, 0.5)
        ymin, ymax = lo - pad, hi + pad
        show_rule = rule is not None and rule <= max(hi * 1.5, hi + 1)
        if show_rule:
            ymax = max(ymax, rule * 1.02)
    ydomain = alt.Scale(domain=[ymin, ymax], nice=False)

    base = alt.Chart(d).encode(
        x=alt.X("time:T", title="Time",
                axis=alt.Axis(format="%d %b %H:%M", labelAngle=-30, tickCount=6, grid=False)),
        y=alt.Y(f"{col}:Q", title=f"{title} ({unit})", scale=ydomain),
        tooltip=[
            alt.Tooltip("time:T", title="Time", format="%d %b %Y %H:%M"),
            alt.Tooltip("building_id:Q", title="Building"),
            alt.Tooltip(f"{col}:Q", title=f"{title} ({unit})", format=".2f"),
            alt.Tooltip("ai_status:N", title="AI status"),
        ],
    )
    layers = []
    if show_rule:
        layers.append(
            alt.Chart(pd.DataFrame({"r": [rule]}))
            .mark_rule(color="#ef4444", strokeDash=[6, 4], strokeWidth=2)
            .encode(y=alt.Y("r:Q", scale=ydomain))
        )
    layers.append(base.mark_line(color=color, strokeWidth=2.5, interpolate="monotone"))
    if mark_status:
        layers.append(
            base.mark_point(size=60, filled=True).encode(
                color=alt.Color("ai_status:N", scale=STATUS_COLORS,
                                legend=alt.Legend(title="AI status"))
            )
        )
    else:
        layers.append(base.mark_point(color=color, size=45, filled=True))
    return alt.layer(*layers).properties(height=height).interactive()


# ---------------------------------------------------------------- pages
def page_overview():
    hero("⚡ Smart Meter Dashboard", "Live electricity monitoring with AI anomaly detection")
    latest = df.iloc[-1]
    if latest["high_reading"]:
        st.error(f"🚨 High Reading Alert: {latest['meter_reading']:.1f} kWh (limit {limit:.0f} kWh)")
    if latest["ai_status"] == "Anomaly":
        st.error("🤖 AI Anomaly Alert: unusual consumption pattern detected")

    prob = latest["anomaly_probability"]
    chance = "-" if pd.isna(prob) else f"{prob * 100:.0f}%"

    c1, c2, c3, c4 = st.columns(4, gap="medium")
    c1.metric("🔋 Latest Reading (kWh)", f"{latest['meter_reading']:.1f}")
    c2.metric("🏢 Building", int(latest["building_id"]))
    c3.metric("🤖 AI Status", latest["ai_status"])
    c4.metric("🎯 Anomaly Chance", chance)
    st.write("")
    c5, c6, c7, c8 = st.columns(4, gap="medium")
    c5.metric("📈 Max Reading (kWh)", f"{df['meter_reading'].max():.1f}")
    c6.metric("📊 Avg Reading (kWh)", f"{df['meter_reading'].mean():.1f}")
    c7.metric("⚠️ Anomaly Count", int((df["ai_status"] == "Anomaly").sum()))
    c8.metric("📥 Readings Received", len(df))
    online = "Online" if mqtt_status["connected"] else "Offline"
    st.caption(
        f"System status: {online} · Data time: {latest['timestamp']} · "
        f"Counts cover the latest {MAX_ROWS} readings."
    )
    st.write("")
    st.subheader("Meter reading trend")
    st.caption(f"Red points = AI anomaly. Red dashed line = high reading limit ({limit:.0f} kWh).")
    st.altair_chart(
        make_chart(df.tail(60), "meter_reading", "Meter reading", "kWh", "#f59e0b",
                   rule=limit, height=300, mark_status=True),
        use_container_width=True,
    )


def page_charts():
    hero("📈 Live Charts", "Real-time meter reading and AI anomaly chance")
    n = st.slider("Readings to show", 10, 200, 60, step=10)
    view = df.tail(n)

    t1, t2 = st.tabs(["🔋 Meter reading", "🎯 Anomaly chance"])
    with t1:
        a, b, c = st.columns(3, gap="medium")
        a.metric("⬇️ Min", f"{view['meter_reading'].min():.1f} kWh")
        b.metric("📊 Average", f"{view['meter_reading'].mean():.1f} kWh")
        c.metric("⬆️ Max", f"{view['meter_reading'].max():.1f} kWh")
        st.write("")
        st.caption(f"Red points = AI anomaly. Red dashed line = high reading limit ({limit:.0f} kWh). "
                   "Hover over a point for exact values.")
        st.altair_chart(
            make_chart(view, "meter_reading", "Meter reading", "kWh", "#f59e0b",
                       rule=limit, mark_status=True),
            use_container_width=True,
        )
    with t2:
        st.caption(f"The AI flags an anomaly when the chance is {AI_THRESHOLD} or higher (red dashed line).")
        st.altair_chart(
            make_chart(view, "anomaly_probability", "Anomaly chance", "0 to 1", "#a78bfa",
                       rule=AI_THRESHOLD, domain=(0, 1), mark_status=True),
            use_container_width=True,
        )


def page_alerts():
    hero("🚨 Alerts", f"Readings above the {limit:.0f} kWh limit")
    hp = df[df["high_reading"]]
    c1, c2, c3 = st.columns(3, gap="medium")
    c1.metric("🚨 Alerts", len(hp))
    c2.metric("📉 Share of readings", f"{100 * len(hp) / len(df):.0f}%")
    c3.metric("🔝 Highest alert (kWh)", f"{hp['meter_reading'].max():.1f}" if len(hp) else "-")
    st.write("")
    if hp.empty:
        st.success(f"✅ No readings above {limit:.0f} kWh.")
    else:
        st.dataframe(
            hp.tail(30).iloc[::-1][["timestamp", "building_id", "meter_reading", "ai_status"]],
            use_container_width=True, hide_index=True,
        )


def page_anomalies():
    hero("🤖 AI Anomalies", "Random Forest trained on labelled Kaggle data flags unusual consumption")
    n_anom = int((df["ai_status"] == "Anomaly").sum())
    c1, c2, c3 = st.columns(3, gap="medium")
    c1.metric("🤖 Anomalies", n_anom)
    c2.metric("✅ Normal readings", len(df) - n_anom)
    c3.metric("📉 Anomaly rate", f"{100 * n_anom / len(df):.1f}%")

    st.write("")
    st.subheader("AI vs real Kaggle label")
    known = df.dropna(subset=["actual_anomaly"])
    if known.empty:
        st.info("The data has no real labels to compare with.")
    else:
        ai = known["ai_status"] == "Anomaly"
        real = known["actual_anomaly"] == 1
        m1, m2, m3, m4 = st.columns(4, gap="medium")
        m1.metric("✅ Caught", int((ai & real).sum()))
        m2.metric("❌ Missed", int((~ai & real).sum()))
        m3.metric("⚠️ False alarms", int((ai & ~real).sum()))
        m4.metric("🎯 Agreement", f"{100 * (ai == real).mean():.0f}%")
        st.caption("Caught = AI and Kaggle both say anomaly. Missed = Kaggle says anomaly, AI says Normal. "
                   "False alarm = AI says anomaly, Kaggle says Normal.")
    st.write("")

    left, right = st.columns(2, gap="large")
    with left:
        st.subheader("Readings by AI status")
        d = df.copy()
        d["time"] = pd.to_datetime(d["timestamp"])
        scatter = (
            alt.Chart(d)
            .mark_circle(size=70, opacity=0.8)
            .encode(
                x=alt.X("time:T", title="Time",
                        axis=alt.Axis(format="%d %b", labelAngle=-30, grid=False)),
                y=alt.Y("meter_reading:Q", title="Meter reading (kWh)",
                        scale=alt.Scale(zero=False)),
                color=alt.Color("ai_status:N", scale=STATUS_COLORS,
                                legend=alt.Legend(title="AI status")),
                tooltip=[
                    alt.Tooltip("time:T", title="Time", format="%d %b %Y %H:%M"),
                    alt.Tooltip("meter_reading:Q", title="kWh", format=".2f"),
                    alt.Tooltip("ai_status:N", title="AI status"),
                ],
            )
            .properties(height=320)
            .interactive()
        )
        st.altair_chart(scatter, use_container_width=True)
    with right:
        st.subheader("Anomaly log")
        if st.session_state.anomaly_log:
            log_df = pd.DataFrame(st.session_state.anomaly_log).iloc[::-1]
            st.dataframe(
                log_df[["timestamp", "building_id", "meter_reading", "anomaly_probability"]],
                use_container_width=True, hide_index=True,
            )
        else:
            st.info("No anomalies detected yet.")


def page_data():
    hero("🗂️ Data & Export", "Recent readings received from the smart meter")
    shown = df.iloc[::-1][[
        "timestamp", "building_id", "meter_reading",
        "anomaly_probability", "ai_status", "actual_anomaly",
    ]]
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

`Kaggle dataset replay → MQTT → HiveMQ Cloud → AI model → Dashboard → Alerts`

- 📡 **MQTT + HiveMQ Cloud** carry the hourly meter readings from the Kaggle dataset.
- 🤖 **Random Forest** (scikit-learn), trained on the labelled Kaggle data, gives every reading an anomaly chance and classifies it as Normal or Anomaly.
- 🎯 **Real labels** from the Kaggle data are shown next to the AI answer, so you can see what it caught and missed.
- 🚨 **High reading alert** fires when a reading goes above the limit you set in the sidebar.

**Tech stack:** Python · Streamlit · paho-mqtt · scikit-learn · SQLite
        """
    )


# ---------------------------------------------------------------- router
if page.endswith("About"):
    page_about()
elif df.empty:
    hero("⚡ Smart Meter Dashboard", "Waiting for the first reading")
    st.info("Waiting for live data from HiveMQ Cloud. Are kaggle_publisher.py and kaggle_live_anomaly.py running?")
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