import json, queue
import streamlit as st
import paho.mqtt.client as mqtt
from streamlit_autorefresh import st_autorefresh

TOPIC = "smartmeter/data"

@st.cache_resource
def start_mqtt():
    q = queue.Queue()
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    c.username_pw_set(st.secrets["HIVEMQ_USER"], st.secrets["HIVEMQ_PASS"])
    c.tls_set()

    def on_connect(client, userdata, flags, reason_code, properties):
        client.subscribe(TOPIC)

    def on_message(client, userdata, msg):
        q.put(json.loads(msg.payload.decode()))

    c.on_connect = on_connect
    c.on_message = on_message
    c.connect(st.secrets["HIVEMQ_HOST"], 8883, 60)
    c.loop_start()
    return q

q = start_mqtt()
st_autorefresh(interval=2000)

if "readings" not in st.session_state:
    st.session_state.readings = []
while not q.empty():
    st.session_state.readings.append(q.get())

st.title("AI-Based Smart Meter Monitoring")
if st.session_state.readings:
    st.dataframe(st.session_state.readings[-20:])
else:
    st.info("Waiting for live data from HiveMQ Cloud")