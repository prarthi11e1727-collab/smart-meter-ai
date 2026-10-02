import streamlit as st
import pandas as pd
import paho.mqtt.client as mqtt
import ssl
import json
import threading

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Smart Meter AI",
    page_icon="⚡",
    layout="wide"
)


# --------------------------------------------------
# MQTT CONNECTION
# --------------------------------------------------

@st.cache_resource
def start_mqtt():

    state = {
        "latest": None,
        "history": [],
        "connected": False,
        "error": None,
        "lock": threading.Lock()
    }

    # ----------------------------------------------
    # MQTT CONNECT
    # ----------------------------------------------

    def on_connect(
        client,
        userdata,
        flags,
        reason_code,
        properties=None
    ):

        print("MQTT CONNECT RESULT:", reason_code)

        if reason_code == 0:

            print("CONNECTED TO HIVEMQ")

            state["connected"] = True
            state["error"] = None

            client.subscribe(
                st.secrets["MQTT_TOPIC"]
            )

            print(
                "SUBSCRIBED TO:",
                st.secrets["MQTT_TOPIC"]
            )

        else:

            state["connected"] = False

            state["error"] = (
                f"Connection failed: {reason_code}"
            )

    # ----------------------------------------------
    # MQTT DISCONNECT
    # ----------------------------------------------

    def on_disconnect(
        client,
        userdata,
        disconnect_flags,
        reason_code,
        properties=None
    ):

        state["connected"] = False

        state["error"] = (
            f"Disconnected: {reason_code}"
        )

        print(
            "MQTT DISCONNECTED:",
            reason_code
        )

    # ----------------------------------------------
    # MQTT MESSAGE
    # ----------------------------------------------

    def on_message(
        client,
        userdata,
        msg
    ):

        try:

            data = json.loads(
                msg.payload.decode()
            )

            print(
                "MQTT MESSAGE RECEIVED:",
                data
            )

            with state["lock"]:

                state["latest"] = data

                state["history"].append(
                    data
                )

                if len(state["history"]) > 100:

                    state["history"].pop(0)

        except Exception as e:

            print(
                "MESSAGE ERROR:",
                repr(e)
            )

    # ----------------------------------------------
    # CREATE MQTT CLIENT
    # ----------------------------------------------

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2
    )

    # ----------------------------------------------
    # MQTT LOGIN
    # ----------------------------------------------

    client.username_pw_set(
        st.secrets["MQTT_USERNAME"],
        st.secrets["MQTT_PASSWORD"]
    )

    # ----------------------------------------------
    # TLS SECURITY
    # ----------------------------------------------

    client.tls_set(
        cert_reqs=ssl.CERT_REQUIRED,
        tls_version=ssl.PROTOCOL_TLS_CLIENT
    )

    # ----------------------------------------------
    # CALLBACKS
    # ----------------------------------------------

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    # ----------------------------------------------
    # CONNECT TO HIVEMQ
    # ----------------------------------------------

    try:

        print("CONNECTING TO HIVEMQ...")

        client.connect(
            st.secrets["MQTT_BROKER"],
            int(st.secrets["MQTT_PORT"]),
            60
        )

        client.loop_start()

        print(
            "MQTT LOOP STARTED"
        )

    except Exception as e:

        state["connected"] = False

        state["error"] = repr(e)

        print(
            "MQTT CONNECTION ERROR:",
            repr(e)
        )

    return state


# --------------------------------------------------
# START MQTT
# --------------------------------------------------

state = start_mqtt()


# --------------------------------------------------
# GET CURRENT DATA
# --------------------------------------------------

with state["lock"]:

    latest = state["latest"]

    history = list(
        state["history"]
    )

    connected = state["connected"]

    mqtt_error = state["error"]


# --------------------------------------------------
# DASHBOARD TITLE
# --------------------------------------------------

st.title(
    "⚡ AI-Based Smart Meter Monitoring"
)

st.subheader(
    "Live IoT Electricity Consumption Dashboard"
)


# --------------------------------------------------
# CONNECTION STATUS
# --------------------------------------------------

if connected:

    st.success(
        "🟢 Connected to HiveMQ Cloud"
    )

else:

    st.warning(
        "🟡 Waiting for live data from HiveMQ Cloud..."
    )

    if mqtt_error:

        st.error(
            f"MQTT Status: {mqtt_error}"
        )

    st.info(
        "Make sure your HiveMQ credentials and "
        "MQTT topic are correct."
    )


# --------------------------------------------------
# LIVE DATA
# --------------------------------------------------

if latest:

    col1, col2, col3, col4 = st.columns(4)

    # Voltage
    col1.metric(
        "Voltage",
        f"{float(latest['voltage']):.2f} V"
    )

    # Current
    col2.metric(
        "Current",
        f"{float(latest['current']):.2f} A"
    )

    # Power
    col3.metric(
        "Power",
        f"{float(latest['power']):.2f} W"
    )

    # Energy
    col4.metric(
        "Energy / Interval",
        f"{float(latest['energy']):.3f}"
    )

    st.divider()

    # --------------------------------------------------
    # LIVE CHARTS
    # --------------------------------------------------

    if history:

        df = pd.DataFrame(
            history
        )

        # Power
        st.subheader(
            "📈 Live Power Consumption"
        )

        st.line_chart(
            df["power"]
        )

        # Voltage
        st.subheader(
            "⚡ Live Voltage"
        )

        st.line_chart(
            df["voltage"]
        )

        # Current
        st.subheader(
            "🔌 Live Current"
        )

        st.line_chart(
            df["current"]
        )

        # --------------------------------------------------
        # RECENT READINGS
        # --------------------------------------------------

        st.subheader(
            "📋 Recent Meter Readings"
        )

        st.dataframe(
            df.tail(20),
            width="stretch"
        )

else:

    st.info(
        "Waiting for the first MQTT message..."
    )