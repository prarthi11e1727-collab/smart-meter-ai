# AI-Based Smart Meter Consumption Anomaly Detection Using IoT

A live dashboard that watches hourly smart meter readings, uses a machine learning model to flag unusual consumption, and shows alerts in real time. Readings travel over MQTT through HiveMQ Cloud, and the dashboard is built with Streamlit.

**Live demo:**  https://appapppy-ghef7im5vzlreggxvafvkg.streamlit.app/
**Demo login:** ask the project owner for the demo username and password.

## How it works

```
Kaggle dataset replay -> MQTT -> HiveMQ Cloud -> AI model -> Dashboard -> Alerts
```

1. **Replay.** Hourly readings for building 107 (year 2016) are replayed one at a time, like a real meter sending data.
2. **MQTT and HiveMQ Cloud.** Each reading is published to the topic `smartmeter/kaggle/data`.
3. **AI model.** A Random Forest (scikit-learn), trained on the labelled Kaggle data, gives every reading an anomaly chance and labels it Normal or Anomaly. The result is published to `smartmeter/kaggle/result`, and flagged readings also go to `smartmeter/kaggle/anomaly`.
4. **Dashboard.** The Streamlit app subscribes to HiveMQ and shows the readings, charts and alerts.

In the deployed site, the replay and the AI scoring run inside the Streamlit app, so nothing has to run on a personal computer.

## Features

- Login page protecting the dashboard
- Overview with latest reading, building, AI status, anomaly chance and summary numbers
- Live charts of meter readings and anomaly chance, with red points for anomalies
- High reading alert, with a limit you can set in the sidebar
- AI vs real label comparison: caught, missed, false alarms and agreement
- Anomaly log and data table, with CSV download
- MQTT feed page showing the raw messages from HiveMQ

## Dataset

A labelled smart meter dataset from Kaggle: A labelled smart meter dataset from Kaggle: Large-scale Energy Anomaly Detection (LEAD), https://www.kaggle.com/competitions/energy-anomaly-detection/data.

| Column | Meaning |
|---|---|
| building_id | The building the reading belongs to (the demo replays building 107) |
| timestamp | Date and hour of the reading, one per hour from 2016-01-01 00:00:00 |
| meter_reading | Electricity consumption for that hour (kWh assumed) |
| anomaly | The real label: 1 = anomaly, 0 = normal |

Rows with missing values are dropped. The dataset has no voltage, current or power columns, so the system works only with hourly consumption.

The model uses these features: `building_id`, `meter_reading`, and `hour`, `day_of_week` and `month` taken from the timestamp.

The full Kaggle training files are not stored in this repository. `dashboard/demo_building_107.csv` is a small file with only building 107, used for the demo.

## Project structure

```
ai/         model training and live scoring, plus the trained model (kaggle_anomaly_model.joblib)
dashboard/  Streamlit app (streamlit_app.py) and the demo data (demo_building_107.csv)
mqtt/       publisher and subscriber scripts for running the flow on a computer
requirements.txt
```

## Run it yourself

1. Install the packages:
   ```
   pip install -r requirements.txt
   ```
2. Create a free HiveMQ Cloud cluster and note its host, username and password.
3. Set these values in a `.env` file (never upload this file) or in Streamlit Secrets:
   ```
   HIVEMQ_HOST = "your-host.s1.eu.hivemq.cloud"
   HIVEMQ_USER = "your-hivemq-username"
   HIVEMQ_PASS = "your-hivemq-password"
   APP_USERNAME = "demo"
   APP_PASSWORD = "your-demo-password"
   ```
4. Start the dashboard:
   ```
   streamlit run dashboard/streamlit_app.py
   ```

## Deploying on Streamlit Community Cloud

1. Push the repository to GitHub.
2. On share.streamlit.io, create an app with the main file `dashboard/streamlit_app.py`.
3. Add the five values above under Settings, then Secrets.
4. In Share, set the app to public.

## Notes

- The free HiveMQ plan has limits on connections, so avoid leaving extra tabs or scripts connected.
- The app sleeps when nobody visits. The first visitor may wait while it wakes up, and the replay then starts again from 1 January.
- Keep `.env` out of GitHub. Use Streamlit Secrets for deployed passwords.

## Tech stack

Python, Streamlit, paho-mqtt, scikit-learn, Altair, pandas, HiveMQ Cloud
