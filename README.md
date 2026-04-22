# SLMS — Smart Log Monitoring System

> **Enterprise-grade, real-time log monitoring with ML-powered anomaly detection.**

---

## 🏗️ Architecture

```
[Log Sources: SSH · Docker · Nginx · Apache · MySQL]
         ↓  (Python agents tail log files)
    [Redis Streams]  ← pipeline / message queue
         ↓
 [FastAPI Processing Engine]
    ├── Feature Engineering  (sliding-window aggregations)
    ├── Isolation Forest ML  (scikit-learn, auto-retrains every 6h)
    ├── Severity Classifier  (5-level: info/warning/medium/high/disaster)
    ├── MongoDB             (all log documents)
    ├── PostgreSQL          (users, alerts)
    └── WebSocket broadcast → React Dashboard
[Alerting: Email (SMTP) + Telegram Bot]
```

## 🚀 Quick Start

### Prerequisites
- Docker Desktop 4.x+
- Docker Compose v2

### 1. Clone & configure
```bash
git clone <repo-url> slms
cd slms
cp .env.example .env   # already done — edit as needed
```

### 2. Start the full stack
```bash
docker compose up -d --build
```

| Service    | URL                            |
|------------|-------------------------------|
| Dashboard  | http://localhost:3000          |
| API docs   | http://localhost:8000/api/docs |
| API        | http://localhost:8000/api/     |

### 3. Default credentials
```
username: admin
password: admin1234
```

### 4. Run the log simulator (generate synthetic events)
```bash
docker exec slms-agents python log_simulator.py --rate 10 --duration 300
```

---

## 📂 Project Structure

```
SLMS/
├── agents/              # Python log collectors (SSH, Nginx, Apache, Docker, MySQL)
│   ├── collectors/      # Per-source tail-F readers
│   ├── parsers/         # Regex log parsers → structured JSON
│   └── log_simulator.py # Synthetic test event generator
├── backend/             # FastAPI application
│   ├── config.py        # pydantic-settings
│   ├── database/        # Motor (MongoDB) + SQLAlchemy (PostgreSQL)
│   ├── models/          # ORM models + Pydantic schemas
│   ├── routes/          # auth · logs · alerts · stats · websocket
│   ├── services/        # ML engine · feature engineering · alerting · GeoIP · pipeline consumer
│   └── middleware/      # JWT auth · rate limiter
├── frontend/            # React + Vite + Tailwind
│   └── src/
│       ├── api/         # Axios API wrappers
│       ├── contexts/    # AuthContext · WebSocketContext
│       ├── pages/       # Dashboard · Logs · Alerts · Settings · Login
│       └── components/  # Charts · LogTable · LiveStream · AlertPanel · Layout
└── docker-compose.yml
```

---

## 🔐 Security

| Feature | Detail |
|---|---|
| Auth | JWT (HS256, 60-min expiry) |
| RBAC | Admin (full) / User (read + ack) |
| Rate limiting | slowapi — 1,000 req/min logs |
| Password hashing | bcrypt |
| Log integrity | MongoDB ObjectId + timestamps |

---

## 🤖 ML Engine

- **Algorithm**: Isolation Forest (`sklearn.ensemble.IsolationForest`)
- **Features (8)**: source-index, HTTP status, is_error, IP request count, IP failure count, global event rate, hour-of-day, response bytes
- **Contamination**: 5% (configurable via `ML_CONTAMINATION`)
- **Auto-retrain**: every 6h on real accumulated data (seeded with synthetic bootstrap on first run)
- **Hybrid severity**: ML score + rule-based triggers → 5-level classification

---

## 📊 Dashboard Features

- **Live log stream** — WebSocket, pausable, filterable
- **Severity distribution** — donut chart
- **Log volume** — area chart (logs + anomalies per hour)
- **Severity trends** — stacked bar chart (24h)
- **Top IPs** — ranked horizontal bar chart
- **System health** — real-time stats card
- **Alert center** — acknowledge / dismiss workflow

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

Alerts fire on **High** and **Disaster** severity events.

---

## 🧪 Testing

```bash
# Simulate SSH brute force + 500 errors + DB crash
docker exec slms-agents python log_simulator.py --rate 20 --duration 60

# Check API
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin1234"}'

# Tail backend logs
docker logs -f slms-backend
```

---

## 📝 API Reference

Full interactive docs: **http://localhost:8000/api/docs**

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/login` | Get JWT token |
| POST | `/api/auth/register` | Create user |
| GET | `/api/logs` | Query logs (paginated, filterable) |
| POST | `/api/logs/ingest` | Direct log ingestion |
| GET | `/api/stats/summary` | Dashboard summary |
| GET | `/api/stats/trend` | Hourly log counts |
| GET | `/api/stats/top-ips` | Top source IPs |
| GET | `/api/alerts` | List alerts |
| PATCH | `/api/alerts/{id}/acknowledge` | Acknowledge alert |
| WS | `/ws/logs?token=<jwt>` | Real-time log stream |

---

## 📦 Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 · Vite · Tailwind CSS · Recharts · React Router |
| Backend | FastAPI · Python 3.11 · Pydantic v2 · SQLAlchemy 2 |
| ML | scikit-learn · Isolation Forest · joblib |
| Databases | MongoDB 7 · PostgreSQL 16 |
| Queue | Redis 7 Streams |
| Auth | python-jose · passlib bcrypt |
| Deployment | Docker · Docker Compose v2 · Nginx |
