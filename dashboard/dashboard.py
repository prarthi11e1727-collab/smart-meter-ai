import pandas as pd
import matplotlib.pyplot as plt
import sqlite3
import os


# ============================================================
# DATABASE
# ============================================================

DB_FILE = os.path.join(
    os.path.dirname(__file__),
    "..",
    "data",
    "smartmeter.db"
)

connection = sqlite3.connect(DB_FILE)

query = """
SELECT timestamp, voltage, current, power, energy
FROM meter_data
ORDER BY id DESC
LIMIT 20
"""

data = pd.read_sql_query(query, connection)

connection.close()


# ============================================================
# PREPARE DATA
# ============================================================

# Reverse data so oldest reading comes first
data = data.iloc[::-1].reset_index(drop=True)

# Convert timestamp
data["timestamp"] = pd.to_datetime(data["timestamp"])


# ============================================================
# CREATE DASHBOARD
# ============================================================

fig, axes = plt.subplots(
    3,
    1,
    figsize=(14, 12)
)

# Main dashboard title
fig.suptitle(
    "Smart Meter Monitoring Dashboard",
    fontsize=20,
    fontweight="bold",
    y=0.97
)


# ============================================================
# X-AXIS LABELS
# ============================================================

number_of_readings = len(data)

if number_of_readings <= 5:

    tick_positions = list(range(number_of_readings))

else:

    tick_positions = [
        round(i * (number_of_readings - 1) / 4)
        for i in range(5)
    ]


tick_labels = [
    data["timestamp"].iloc[i].strftime("%H:%M:%S")
    for i in tick_positions
]


# ============================================================
# 1. VOLTAGE
# ============================================================

axes[0].plot(
    data.index,
    data["voltage"],
    marker="o",
    linewidth=2
)

axes[0].set_title(
    "Voltage Monitoring",
    fontsize=15,
    pad=15
)

axes[0].set_ylabel(
    "Voltage (V)",
    fontsize=12
)

axes[0].set_xticks(tick_positions)
axes[0].set_xticklabels(tick_labels)

axes[0].grid(
    True,
    alpha=0.3
)


# ============================================================
# 2. CURRENT
# ============================================================

axes[1].plot(
    data.index,
    data["current"],
    marker="o",
    linewidth=2
)

axes[1].set_title(
    "Current Monitoring",
    fontsize=15,
    pad=15
)

axes[1].set_ylabel(
    "Current (A)",
    fontsize=12
)

axes[1].set_xticks(tick_positions)
axes[1].set_xticklabels(tick_labels)

axes[1].grid(
    True,
    alpha=0.3
)


# ============================================================
# 3. POWER
# ============================================================

axes[2].plot(
    data.index,
    data["power"],
    marker="o",
    linewidth=2
)

axes[2].set_title(
    "Power Consumption",
    fontsize=15,
    pad=15
)

axes[2].set_ylabel(
    "Power (W)",
    fontsize=12
)

axes[2].set_xlabel(
    "Time",
    fontsize=12
)

axes[2].set_xticks(tick_positions)
axes[2].set_xticklabels(tick_labels)

axes[2].grid(
    True,
    alpha=0.3
)


# ============================================================
# SPACING
# ============================================================

plt.subplots_adjust(
    top=0.86,
    bottom=0.08,
    left=0.09,
    right=0.97,
    hspace=0.85
)


# ============================================================
# SHOW DASHBOARD
# ============================================================

plt.show()