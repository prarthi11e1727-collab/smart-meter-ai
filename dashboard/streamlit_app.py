import streamlit as st
import pandas as pd
import sqlite3
import os

# Page configuration
st.set_page_config(
    page_title="Smart Meter AI",
    page_icon="⚡",
    layout="wide"
)

# Database path
DB_FILE = os.path.join(
    os.path.dirname(__file__),
    "..",
    "data",
    "smartmeter.db"
)

# Read database
connection = sqlite3.connect(DB_FILE)

query = """
SELECT timestamp, voltage, current, power, energy
FROM meter_data
ORDER BY id DESC
LIMIT 20
"""

data = pd.read_sql_query(query, connection)
connection.close()

# Reverse order for display
data = data.iloc[::-1].reset_index(drop=True)

# Title
st.title("⚡ AI-Based Smart Meter Monitoring")
st.subheader("Real-Time Electricity Consumption Dashboard")

# Current values
if not data.empty:

    latest = data.iloc[-1]

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Voltage", f"{latest['voltage']:.2f} V")
    col2.metric("Current", f"{latest['current']:.2f} A")
    col3.metric("Power", f"{latest['power']:.2f} W")
    col4.metric("Energy", f"{latest['energy']:.3f}")

    st.divider()

    # Power chart
    st.subheader("Power Consumption")
    st.line_chart(
        data.set_index("timestamp")["power"]
    )

    # Voltage chart
    st.subheader("Voltage")
    st.line_chart(
        data.set_index("timestamp")["voltage"]
    )

    # Current chart
    st.subheader("Current")
    st.line_chart(
        data.set_index("timestamp")["current"]
    )

    # Recent readings
    st.subheader("Recent Meter Readings")
    st.dataframe(
        data,
        use_container_width=True
    )

else:
    st.warning("No meter data available.")