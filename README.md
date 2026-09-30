\# AI-Based Smart Meter Consumption Anomaly Detection Using IoT



\## 📌 Project Overview



This project presents an IoT-based smart meter monitoring system that collects electricity consumption data, stores it, analyzes it using Machine Learning, and displays the results on a real-time dashboard.



The system uses synthetic smart meter data for development and testing. MQTT is used for communication, HiveMQ Cloud acts as the MQTT broker, SQLite stores the readings, and an Isolation Forest Machine Learning model detects unusual consumption patterns.



\## 🎯 Objectives



\- Generate smart meter electricity consumption data.

\- Transmit meter readings using MQTT.

\- Use HiveMQ Cloud as the MQTT broker.

\- Store readings in an SQLite database.

\- Monitor voltage, current, power and energy.

\- Detect unusual consumption using Machine Learning.

\- Display live readings on a dashboard.

\- Generate alerts for high power consumption and AI-detected anomalies.

\- Maintain the project using Git and GitHub.



\## 🏗️ System Architecture



Synthetic Data Generator

&#x20;       ↓

&#x20;     MQTT

&#x20;       ↓

&#x20;  HiveMQ Cloud

&#x20;       ↓

&#x20;    SQLite

&#x20;       ↓

&#x20;     AI / ML

&#x20;       ↓

&#x20;   Node-RED

&#x20;       ↓

&#x20;   Dashboard

&#x20;       ↓

&#x20;     Alert



\## 🔧 Technologies Used



\### Programming

\- Python

\- JavaScript



\### IoT and Communication

\- MQTT

\- HiveMQ Cloud



\### Database

\- SQLite



\### Machine Learning

\- Scikit-learn

\- Isolation Forest



\### Dashboard and Automation

\- Node-RED

\- FlowFuse Dashboard



\### Development Tools

\- VS Code

\- Git

\- GitHub



\## 📊 Parameters Monitored



The system monitors:



\- Voltage (V)

\- Current (A)

\- Power (W)

\- Energy



Power is calculated using:



Power = Voltage × Current



\## 🤖 Anomaly Detection



The project uses the Isolation Forest algorithm from Scikit-learn.



The model analyzes:



\- Voltage

\- Current

\- Power

\- Energy



Each reading is classified as either:



\- Normal

\- Anomaly



The Machine Learning anomaly detection is different from the fixed high-power alert. A reading can be considered unusual by the ML model even when it does not cross the fixed power threshold.



\## 🚨 Alert System



The system provides two types of alerts.



\### High Power Alert



A threshold-based alert is generated when:



Power > 1000 W



\### AI Anomaly Alert



An alert is generated when the Machine Learning model identifies an unusual consumption pattern.



\## 📈 Dashboard



The Node-RED dashboard provides:



\- Latest Power

\- Voltage

\- Current

\- Energy

\- Maximum Power

\- Average Power

\- System Status

\- Power Monitoring Graph

\- Voltage Monitoring Graph

\- Current Monitoring Graph

\- Recent Smart Meter Readings

\- AI Anomaly Status

\- AI Anomaly Count

\- AI Anomaly Log

\- High Power Alerts

\- AI Anomaly Alerts



\## 🔐 Login System



A basic dashboard login page has been implemented using Node-RED Dashboard.



The login page contains:



\- Username

\- Password

\- Login button

\- Login status



The password field uses password input mode so that the entered password is hidden.



\## 📁 Project Structure



```text

smart-meter-ai/

│

├── ai/

│   ├── anomaly\_detection.py

│   └── live\_anomaly.py

│

├── dashboard/

│   └── dashboard.py

│

├── data/

│   ├── database.py

│   └── synthetic\_data.csv

│

├── mqtt/

│   ├── publisher.py

│   └── subscriber.py

│

├── .gitignore

├── electricity\_data.csv

├── generate\_data.py

├── plot\_data.py

├── Figure\_1.png

└── README.md

