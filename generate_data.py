import pandas as pd
import numpy as np

# Make the results reproducible
np.random.seed(42)

# 24 hours of electricity consumption
hours = np.arange(0, 24)

# Normal household consumption pattern
consumption = np.array([
    0.8, 0.7, 0.6, 0.6, 0.7, 1.0,
    1.5, 2.0, 1.8, 1.4, 1.2, 1.1,
    1.0, 1.1, 1.2, 1.4, 1.8, 2.5,
    3.0, 3.5, 3.2, 2.5, 1.8, 1.2
])

# Add small random variations
consumption = consumption + np.random.normal(0, 0.1, 24)
# Add abnormal electricity consumption
consumption[20] = 10.0

# Create DataFrame
data = pd.DataFrame({
    "Hour": hours,
    "Power_kW": consumption
})

# Save as CSV
data.to_csv("electricity_data.csv", index=False)

print("Dataset created successfully!")
print(data)