import pandas as pd
import matplotlib.pyplot as plt

# Read the electricity dataset
data = pd.read_csv("electricity_data.csv")

# Create the graph
plt.plot(data["Hour"], data["Power_kW"], marker="o")

# Add labels
plt.xlabel("Hour")
plt.ylabel("Power Consumption (kW)")
plt.title("Electricity Consumption Over 24 Hours")

# Show grid
plt.grid(True)

# Display graph
plt.show()