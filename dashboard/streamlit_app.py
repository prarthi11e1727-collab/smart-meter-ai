import streamlit as st
import pandas as pd
import os

st.set_page_config(
    page_title="Smart Meter AI",
    page_icon="⚡",
    layout="wide"
)

# CSV path
CSV_FILE = os.path.join(
    os.path.dirname(__file__),
    "..",
    "data",
    "synthetic_data.csv"
)

# Read data
data = pd.read_csv(CSV_FILE)

# Latest reading
latest = data.iloc[-1]

st.title("⚡ AI-Based Smart Meter Monitoring")
st.subheader("Real-Time Electricity Consumption Dashboard")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Voltage", f"{latest['voltage']:.2f} V")
col2.metric("Current", f"{latest['current']:.2f} A")
col3.metric("Power", f"{latest['power']:.2f} W")
col4.metric("Energy", f"{latest['energy']:.3f}")

st.divider()

st.subheader("Power Consumption")
st.line_chart(data["power"])

st.subheader("Voltage")
st.line_chart(data["voltage"])

st.subheader("Current")
st.line_chart(data["current"])

st.subheader("Recent Meter Readings")
st.dataframe(data.tail(20), width="stretch")