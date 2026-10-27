
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score
)

# Kaggle dataset path
DATA_FILE = Path("data/train.csv")

print("Loading Kaggle smart-meter dataset...")

# Load only the required columns
data = pd.read_csv(
    DATA_FILE,
    usecols=["building_id", "timestamp", "meter_reading", "anomaly"]
)

print("Total records loaded:", len(data))

# Remove records without a usable consumption reading or label
data = data.dropna(
    subset=["building_id", "timestamp", "meter_reading", "anomaly"]
).copy()

# Convert timestamp into useful numerical features
data["timestamp"] = pd.to_datetime(data["timestamp"], errors="coerce")
data = data.dropna(subset=["timestamp", "meter_reading", "anomaly"])

data["hour"] = data["timestamp"].dt.hour
data["day_of_week"] = data["timestamp"].dt.dayofweek
data["month"] = data["timestamp"].dt.month

# Input features: do NOT include the anomaly label
feature_columns = [
    "building_id",
    "meter_reading",
    "hour",
    "day_of_week",
    "month"
]

X = data[feature_columns]
y = data["anomaly"].astype(int)

print("\nUsable records:", len(data))
print("Class distribution:")
print(y.value_counts())

# Use a manageable, reproducible sample for the first experiment
if len(data) > 100_000:
    sample = data.sample(n=100_000, random_state=42)
    X = sample[feature_columns]
    y = sample["anomaly"].astype(int)

# Keep anomaly proportions similar in training and testing
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

print("\nTraining Random Forest model...")

model = RandomForestClassifier(
    n_estimators=100,
    class_weight="balanced",
    random_state=42,
    n_jobs=-1
)

model.fit(X_train, y_train)

# Evaluate on records not used for training
predictions = model.predict(X_test)
probabilities = model.predict_proba(X_test)[:, 1]

print("\nKaggle Smart-Meter Anomaly Detection Results")
print("--------------------------------------------")
print(classification_report(
    y_test,
    predictions,
    target_names=["Normal", "Anomaly"],
    zero_division=0
))

print("Confusion matrix:")
print(confusion_matrix(y_test, predictions))

print("ROC-AUC:", round(roc_auc_score(y_test, probabilities), 4))

# Save the trained model
import joblib

output_file = Path("ai/kaggle_anomaly_model.joblib")
joblib.dump(model, output_file)

print("\nModel saved to:", output_file)
