import streamlit as st
import pandas as pd
import paho.mqtt.client as mqtt
import ssl
import json
import threading
import time
import uuid


# ============================================================
# PAGE SETTINGS
# ============================================================

st.set_page_config(
    page_title="Smart Meter AI",
    page_icon="⚡",
    layout="wide"
)


# ============================================================
# MQTT CONNECTION
# ============================================================

@st.cache_resource
def start_mqtt():

    state = {
        "latest": None,
        "history": [],
        "connected": False,
        "error": None,
        "lock": threading.Lock()
    }

    # --------------------------------------------------------
    # WHEN CONNECTED
    # --------------------------------------------------------

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

            with state["lock"]:
                state["connected"] = True
                state["error"] = None

            result = client.subscribe(
                st.secrets["MQTT_TOPIC"]
            )

            print(
                "SUBSCRIBE RESULT:",
                result
            )

            print(
                "SUBSCRIBED TO:",
                st.secrets["MQTT_TOPIC"]
            )

        else:

            with state["lock"]:
                state["connected"] = False
                state["error"] = (
                    f"Connection failed: {reason_code}"
                )

            print(
                "MQTT CONNECTION FAILED:",
                reason_code
            )


    # --------------------------------------------------------
    # WHEN DISCONNECTED
    # --------------------------------------------------------

    def on_disconnect(
        client,
        userdata,
        disconnect_flags,
        reason_code,
        properties=None
    ):

        print(
            "MQTT DISCONNECTED:",
            reason_code
        )

        with state["lock"]:
            state["connected"] = False
            state["error"] = (
                f"Disconnected: {reason_code}"
            )


    # --------------------------------------------------------
    # WHEN MESSAGE ARRIVES
    # --------------------------------------------------------

    def on_message(
        client,
        userdata,
        msg
    ):

        try:

            data = json.loads(
                msg.payload.decode("utf-8")
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


    # ========================================================
    # CREATE MQTT CLIENT
    # ========================================================

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="streamlit-" + uuid.uuid4().hex[:12],
        protocol=mqtt.MQTTv311,
        transport="websockets"
    )


    # ========================================================
    # MQTT LOGIN
    # ========================================================

    client.username_pw_set(
        st.secrets["MQTT_USERNAME"],
        st.secrets["MQTT_PASSWORD"]
    )


    # ========================================================
    # TLS
    # ========================================================

    client.tls_set(
        cert_reqs=ssl.CERT_REQUIRED,
        tls_version=ssl.PROTOCOL_TLS_CLIENT
    )


    # ========================================================
    # WEBSOCKET PATH
    # ========================================================

    client.ws_set_options(
        path="/mqtt"
    )


    # ========================================================
    # CALLBACKS
    # ========================================================

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message


    # ========================================================
    # CONNECT
    # ========================================================

    try:

        print(
            "CONNECTING TO HIVEMQ USING WEBSOCKETS..."
        )

        client.connect(
            st.secrets["MQTT_BROKER"],
            8884,
            60
        )

        client.loop_start()

        print(
            "MQTT WEBSOCKET LOOP STARTED"
        )

    except Exception as e:

        print(
            "MQTT CONNECTION ERROR:",
            repr(e)
        )

        with state["lock"]:
            state["connected"] = False
            state["error"] = repr(e)


    return state


# ============================================================
# START MQTT
# ============================================================

state = start_mqtt()


# ============================================================
# DASHBOARD DISPLAY
# ============================================================

@st.fragment(run_every=2)
def display_dashboard():

    with state["lock"]:

        latest = state["latest"]

        history = list(
            state["history"]
        )

        connected = state["connected"]

        mqtt_error = state["error"]


    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    st.title(
        "⚡ AI-Based Smart Meter Monitoring"
    )

    st.subheader(
        "Live IoT Electricity Consumption Dashboard"
    )


    # --------------------------------------------------------
    # CONNECTION STATUS
    # --------------------------------------------------------

    if connected:

        st.success(
            "🟢 Connected to HiveMQ Cloud"
        )

    else:

        st.warning(
            "⏳ Waiting for live data from HiveMQ Cloud..."
        )

        if mqtt_error:

            st.error(
                f"MQTT Status: {mqtt_error}"
            )


    # --------------------------------------------------------
    # LIVE DATA
    # --------------------------------------------------------

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


        st.divider()


        # ----------------------------------------------------
        # CHARTS
        # ----------------------------------------------------

        if history:

            df = pd.DataFrame(
                history
            )


            st.subheader(
                "📈 Live Power Consumption"
            )

            st.line_chart(
                df["power"]
            )


            st.subheader(
                "⚡ Live Voltage"
            )

            st.line_chart(
                df["voltage"]
            )


            st.subheader(
                "🔌 Live Current"
            )

            st.line_chart(
                df["current"]
            )


            # ------------------------------------------------
            # RECENT READINGS
            # ------------------------------------------------

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


# ============================================================
# RUN DASHBOARD
# ============================================================

display_dashboard()