# SLMS — Smart Log Monitoring System

> **Enterprise-grade, real-time log monitoring with ML-powered anomaly detection.**

## 📖 Project Overview

The Smart Log Monitoring System (SLMS) is a comprehensive, full-stack application designed to aggregate, process, analyze, and visualize logs from various sources (SSH, Docker, Nginx, Apache, MySQL) in real-time. By leveraging a robust pipeline architecture and Machine Learning (Isolation Forest), SLMS detects anomalies, classifies log severities, and alerts administrators about potential security threats or system failures.

This project is built to provide an intuitive dashboard for security operations, offering deep insights into system health, service status, and potential attack vectors.

---

## ✨ Key Features & Recent Updates

- **Real-Time Log Pipeline**: High-throughput log ingestion using Redis Streams and Python-based collectors.
- **Machine Learning Anomaly Detection**: Unsupervised learning (Isolation Forest) to detect unusual patterns, automatically retraining every 6 hours.
- **Service Sentinel**: Real-time service monitoring component tracking the health of backend services and databases.
- **System Health Tray**: Persistent UI component providing a quick glance at total, high, and critical log counts.
- **Advanced Log Simulator**: Built-in simulator with granular `train` and `attack` modes, featuring percentage-based severity distribution ratios for realistic training scenarios.
- **Threshold-based Security Posture**: Intelligent dashboard logic calculating system health based on severity thresholds rather than raw event counts.
- **Global Timestamp Stripping**: Enhanced ML accuracy and UI readability through robust log cleaning prior to ingestion.
- **Interactive Dashboard**: WebSocket-powered live log streams, 24h severity trends, anomaly distribution charts, and top IP trackers.
- **Automated Alerting**: Immediate email (SMTP) and Telegram notifications for High and Disaster severity events.

---

## 🏗️ Architecture & Working Process

The SLMS architecture is designed for scalability and real-time processing:

### 1. Data Ingestion (Agents)
Python-based agents run alongside monitored services, tailing log files in real-time. They parse raw logs using regex patterns, convert them into structured JSON, and push them into **Redis Streams**, which acts as a high-throughput message queue.

### 2. Processing Engine (FastAPI)
A FastAPI-based consumer constantly reads from Redis. It performs:
- **Data Cleaning**: Strips out unnecessary characters and extracts timestamps.
- **Feature Engineering**: Calculates sliding-window aggregations (e.g., requests per minute, error rates).
- **ML Inference**: Feeds the engineered features into a pre-trained scikit-learn Isolation Forest model.
- **Severity Classification**: Combines ML anomaly scores with rule-based heuristics to assign a severity (Info, Warning, Medium, High, Disaster).

### 3. Storage
- **MongoDB**: Stores all processed log documents for fast querying and archiving.
- **PostgreSQL**: Manages structured relational data, including User accounts, Roles, and generated Alerts.

### 4. Presentation (React Frontend)
Processed logs and calculated statistics are broadcasted via WebSockets to the React frontend. The UI updates dynamically, rendering charts, updating the Service Sentinel, and pushing real-time events to the Log Table.

---

## 🧩 System Components

1. **Frontend Application (React/Vite)**: The user interface providing dashboards, log viewers, alert management, and system settings.
2. **Backend Server (FastAPI)**: The core API serving REST endpoints, WebSocket connections, and managing background tasks.
3. **Log Processing Pipeline**: The Redis consumer and Python processing logic that handles ML inference and DB writes.
4. **Log Collectors/Agents**: Lightweight Python scripts running on edge nodes to capture logs.
5. **Log Simulator**: A testing tool to generate synthetic logs mimicking normal traffic or cyber-attacks.
6. **Machine Learning Engine**: The Isolation Forest model and its automated retraining pipeline.

---

## 👥 Actors & Role-Based Access Control (RBAC)

SLMS implements a strict Role-Based Access Control system to ensure security and operational integrity.

### 2. Admin (Administrator)
- **Permissions**: Full access to the system.
- **Capabilities**: View all logs, acknowledge/dismiss alerts, manage system settings, trigger ML model retraining, view service health, and manage users.

### 2. User (Analyst/Operator)
- **Permissions**: Read-only and operational access.
- **Capabilities**: View dashboard statistics, read log streams, and acknowledge alerts. Cannot modify system configurations or manage users.

### 3. System Agent (Non-Human Actor)
- **Permissions**: Write-only for log ingestion.
- **Capabilities**: Push structured logs to the Redis queue. Restricted from reading data or accessing management endpoints.

---

## 📂 Project Structure

```text
SLMS/
├── agents/              # Python log collectors and simulator
│   ├── collectors/      # Per-source tail-F readers (SSH, Nginx, etc.)
│   ├── parsers/         # Regex log parsers mapping strings to JSON
│   └── log_simulator.py # Synthetic test event generator (Train/Attack modes)
├── backend/             # FastAPI application
│   ├── config.py        # Environment variables and settings
│   ├── database/        # Motor (MongoDB) + SQLAlchemy (PostgreSQL) setups
│   ├── models/          # ORM models and Pydantic validation schemas
│   ├── routes/          # REST API routers (auth, logs, alerts, stats)
│   ├── services/        # ML engine, feature engineering, alerting, WebSocket logic
│   └── middleware/      # JWT authentication and slowapi rate limiting
├── frontend/            # React + Vite application
│   └── src/
│       ├── api/         # Axios API clients
│       ├── components/  # Reusable UI (Charts, Service Sentinel, Health Tray, Log Table)
│       ├── contexts/    # React Contexts (Auth, WebSockets, Theme)
│       └── pages/       # Route views (Dashboard, Logs, Alerts, Settings)
└── docker-compose.yml   # Container orchestration configuration
```

---

## 🚀 Installation & Running the Project

### Prerequisites
- **Docker Desktop 4.x+** or Docker Engine
- **Docker Compose v2**
- Git

### 1. Clone & Configure
```bash
git clone <repo-url> slms
cd slms
# The .env.example file is provided. Create a .env file based on it.
cp .env.example .env 
```

### 2. Start the Stack
Bring up the entire system (Frontend, Backend, DBs, Redis, Agents) using Docker Compose:
```bash
docker compose up -d --build
```

### 3. Accessing the System
| Service | URL |
|---|---|
| Dashboard | http://localhost:3000 |
| REST API | http://localhost:8000/api/ |
| Swagger Docs | http://localhost:8000/api/docs |

### 4. Default Credentials
- **Username**: `admin`
- **Password**: `admin1234`

---
## 🔔 Alerting

Set in `.env`:

```env
ENABLE_EMAIL=true
SMTP_HOST=smtp.gmail.com
SMTP_USER=you@gmail.com
SMTP_PASSWORD=app-password

ENABLE_TELEGRAM=true
TELEGRAM_BOT_TOKEN=123456:ABCdef...
TELEGRAM_CHAT_ID=@yourchannel
```
## 🧪 Usage & Log Simulator Guide

To test the system's capabilities, you can generate synthetic logs using the built-in simulator container.

**Generate random background noise:**
```bash
docker exec slms-agents python log_simulator.py --rate 10 --duration 300
```

**Generate "Train" mode logs (Standard healthy traffic):**
*Generates mostly Info/Warning logs to establish a healthy baseline.*
```bash
docker exec slms-agents python log_simulator.py --mode train --duration 60 --rate 20
```

**Generate "Attack" mode logs (Simulated threats):**
*Generates High/Disaster logs (e.g., SSH Brute Force, DB crashes) to trigger the ML anomaly detector and alerts.*
```bash
docker exec slms-agents python log_simulator.py --mode attack --duration 30 --rate 5
```

---

## 🔐 Security

SLMS incorporates multiple layers of security:
- **Authentication**: JWT-based authentication (HS256 signature, 60-minute expiry).
- **Password Security**: Passwords hashed using `bcrypt`.
- **API Rate Limiting**: `slowapi` restricts log query endpoints to 1,000 requests/minute to prevent abuse.
- **Data Integrity**: MongoDB ObjectIds and immutable timestamps ensure log trails cannot be easily manipulated.

---

## 📦 Technology Stack

| Component | Technologies Used |
|---|---|
| **Frontend** | React 18, Vite, Tailwind CSS, Recharts, React Router, Lucide Icons |
| **Backend** | FastAPI, Python 3.11, Pydantic v2, SQLAlchemy 2 |
| **Machine Learning** | scikit-learn, Isolation Forest, joblib, numpy, pandas |
| **Databases** | MongoDB 7 (Logs), PostgreSQL 16 (Users/Alerts) |
| **Message Broker** | Redis 7 Streams |
| **Deployment** | Docker, Docker Compose, Nginx |

---

## 🙌 Acknowledgements

This project was developed to provide a modern, robust, and intelligent approach to log monitoring and system security. Special thanks to the open-source communities behind **React**, **FastAPI**, **scikit-learn**, and **Docker**, whose tools made this architecture possible.

---
*Generated for the Smart Log Monitoring System (SLMS) documentation.
---



