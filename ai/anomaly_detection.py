import sqlite3
import pandas as pd
from sklearn.ensemble import IsolationForest

DB_FILE = r"C:\Users\neha mishra\Desktop\smart meter ai\data\smartmeter.db"

# Connect to SQLite
connection = sqlite3.connect(DB_FILE)

# Read smart meter data
query = """
SELECT timestamp, voltage, current, power, energy
FROM meter_data
"""

data = pd.read_sql_query(query, connection)
connection.close()

# Check whether enough data is available
if len(data) < 10:
    print("Not enough data for anomaly detection.")
    print("Collect at least 10 readings first.")
    exit()

# Select features for ML
features = data[["voltage", "current", "power", "energy"]]

# Create Isolation Forest model
model = IsolationForest(
    contamination=0.10,
    random_state=42
)

# Train and predict
data["anomaly"] = model.fit_predict(features)

# Convert ML output
data["status"] = data["anomaly"].map({
    1: "Normal",
    -1: "Anomaly"
})

# Display latest results
print("\nAI-Based Smart Meter Anomaly Detection")
print("---------------------------------------")

print(
    data[
        ["timestamp", "voltage", "current", "power", "status"]
    ].tail(10).to_string(index=False)
)

# Count anomalies
anomaly_count = (data["status"] == "Anomaly").sum()

print("\nTotal readings:", len(data))
print("Anomalies detected:", anomaly_count)
