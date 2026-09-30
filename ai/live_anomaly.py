import sqlite3
import pandas as pd
from sklearn.ensemble import IsolationForest
import json

DB_FILE = r"C:\Users\neha mishra\Desktop\smart meter ai\data\smartmeter.db"

# Connect to database
connection = sqlite3.connect(DB_FILE)

query = """
SELECT timestamp, voltage, current, power, energy
FROM meter_data
ORDER BY id
"""

data = pd.read_sql_query(query, connection)
connection.close()

# Need enough readings for ML
if len(data) < 10:
    print(json.dumps({
        "status": "Not Enough Data"
    }))
    exit()

# Features used by the AI model
features = data[["voltage", "current", "power", "energy"]]

# Isolation Forest
model = IsolationForest(
    contamination=0.10,
    random_state=42
)

data["prediction"] = model.fit_predict(features)

# Latest reading
latest = data.iloc[-1]

status = "Anomaly" if latest["prediction"] == -1 else "Normal"

result = {
    "timestamp": latest["timestamp"],
    "voltage": float(latest["voltage"]),
    "current": float(latest["current"]),
    "power": float(latest["power"]),
    "energy": float(latest["energy"]),
    "status": status
}

print(json.dumps(result))