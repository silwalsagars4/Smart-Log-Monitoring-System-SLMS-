# Smart Log Monitoring System (SLMS) — Implementation Plan

## Overview

A production-grade, containerized log monitoring platform that ingests logs from SSH, Docker, Nginx, Apache, and MySQL; processes them through a Redis-backed pipeline; applies Isolation Forest anomaly detection; classifies into 5 severity levels; and surfaces insights in a modern React dashboard with real-time WebSocket streaming, JWT auth, alerting (Email + Telegram), and GeoIP support.

---

## Architecture Decision Summary

| Component | Technology | Rationale |
|---|---|---|
| Frontend | React + Vite + Tailwind + Recharts | Fast build, great DX, modern UI |
| Backend API | FastAPI (Python 3.11) | Async, WebSocket, auto OpenAPI docs |
| Log Pipeline | Redis Streams | Lightweight, persistent, ordered |
| Primary Store | MongoDB | Flexible schema for log documents |
| Relational Store | PostgreSQL | Users, alerts, config |
| ML Engine | scikit-learn Isolation Forest | Built-in, well-supported |
| Alerting | SMTP + Telegram Bot API | Simple, no extra infra |
| Deployment | Docker + Docker Compose v2 | Reproducible, portable |
| GeoIP | MaxMind GeoLite2 (city) | Free, accurate |

---

## Repository Structure

```
c:\projects\SLMS\
├── docker-compose.yml
├── .env.example
├── README.md
│
├── agents/                        # Log collector agents
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                    # Agent orchestrator
│   ├── collectors/
│   │   ├── base_collector.py
│   │   ├── ssh_collector.py
│   │   ├── nginx_collector.py
│   │   ├── apache_collector.py
│   │   ├── docker_collector.py
│   │   └── mysql_collector.py
│   ├── parsers/
│   │   ├── base_parser.py
│   │   ├── ssh_parser.py
│   │   ├── nginx_parser.py
│   │   ├── apache_parser.py
│   │   ├── docker_parser.py
│   │   └── mysql_parser.py
│   └── log_simulator.py           # Test data generator
│
├── backend/                       # FastAPI application
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                    # App entry point
│   ├── config.py                  # Settings (pydantic-settings)
│   ├── database/
│   │   ├── mongo.py               # Motor async client
│   │   └── postgres.py            # SQLAlchemy async
│   ├── models/
│   │   ├── log.py                 # Pydantic + Mongo models
│   │   ├── user.py
│   │   └── alert.py
│   ├── routes/
│   │   ├── auth.py                # JWT login/register
│   │   ├── logs.py                # CRUD + filter
│   │   ├── alerts.py
│   │   ├── stats.py               # Aggregations for charts
│   │   └── ws.py                  # WebSocket streaming
│   ├── services/
│   │   ├── ml_engine.py           # Isolation Forest
│   │   ├── feature_engineer.py
│   │   ├── severity_classifier.py
│   │   ├── alert_service.py       # Email + Telegram
│   │   ├── geoip_service.py
│   │   └── pipeline_consumer.py   # Redis Streams consumer
│   └── middleware/
│       ├── auth_middleware.py
│       └── rate_limiter.py
│
└── frontend/                      # React + Vite
    ├── Dockerfile
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── api/
        │   ├── client.js           # Axios instance
        │   ├── logs.js
        │   ├── auth.js
        │   └── stats.js
        ├── contexts/
        │   ├── AuthContext.jsx
        │   └── WebSocketContext.jsx
        ├── pages/
        │   ├── Login.jsx
        │   ├── Dashboard.jsx
        │   ├── Logs.jsx
        │   ├── Alerts.jsx
        │   └── Settings.jsx
        └── components/
            ├── Layout/
            │   ├── Sidebar.jsx
            │   ├── Header.jsx
            │   └── Layout.jsx
            ├── Charts/
            │   ├── LogsPerSecondChart.jsx
            │   ├── ErrorTrendChart.jsx
            │   ├── SeverityDistributionChart.jsx
            │   └── TopIPsChart.jsx
            ├── LogTable.jsx
            ├── SeverityBadge.jsx
            ├── AlertPanel.jsx
            ├── SystemHealthCard.jsx
            └── LiveLogStream.jsx
```

---

## Proposed Changes

### Component 1 — Infrastructure

#### [NEW] docker-compose.yml
Full compose stack: frontend, backend, agents, redis, mongo, postgres

#### [NEW] .env.example
All environment variables with documentation

---

### Component 2 — Log Agents

#### [NEW] agents/collectors/base_collector.py
Abstract tail-F reader with rotation handling, Redis publish

#### [NEW] agents/collectors/ssh_collector.py
Reads `/var/log/auth.log`

#### [NEW] agents/collectors/nginx_collector.py
Reads `/var/log/nginx/access.log`

#### [NEW] agents/collectors/apache_collector.py
Reads `/var/log/apache2/access.log`

#### [NEW] agents/collectors/docker_collector.py
Polls Docker daemon via SDK

#### [NEW] agents/collectors/mysql_collector.py
Reads `/var/log/mysql/error.log`

#### [NEW] agents/parsers/*.py
Regex-based structured log extraction for each source

#### [NEW] agents/log_simulator.py
Generates synthetic brute-force, 500 errors, crash events for testing

---

### Component 3 — Backend

#### [NEW] backend/config.py
`pydantic-settings` with environment variable binding

#### [NEW] backend/database/mongo.py + postgres.py
Async Motor + SQLAlchemy connections with connection pools

#### [NEW] backend/services/ml_engine.py
- Trains Isolation Forest on feature vectors
- Serializes model with joblib
- Provides `predict(feature_vector) → (score, is_anomaly)`

#### [NEW] backend/services/feature_engineer.py
Sliding window aggregations: event frequency, failed logins, error ratio

#### [NEW] backend/services/severity_classifier.py
Hybrid: ML score + rule engine → 5-level severity

#### [NEW] backend/services/pipeline_consumer.py
Background task that reads Redis Streams, runs ML, writes to Mongo

#### [NEW] backend/services/alert_service.py
Async email (SMTP) + Telegram Bot dispatch for High/Disaster

#### [NEW] backend/services/geoip_service.py
MaxMind GeoLite2 city lookup → lat/lon/country

#### [NEW] backend/routes/auth.py
POST /auth/login, POST /auth/register, JWT refresh

#### [NEW] backend/routes/logs.py
GET /logs (paginated, filterable by source/severity/time/search)
POST /logs/ingest (direct ingestion endpoint)

#### [NEW] backend/routes/stats.py
GET /stats/summary, GET /stats/top-ips, GET /stats/trend

#### [NEW] backend/routes/ws.py
WebSocket /ws/logs — streams anomalies in real-time

---

### Component 4 — Frontend

#### [NEW] frontend/src/pages/Dashboard.jsx
Hero stats, charts grid, live stream panel

#### [NEW] frontend/src/pages/Logs.jsx  
Paginated table with search, severity/source filter

#### [NEW] frontend/src/pages/Alerts.jsx
Alert history with acknowledge/dismiss

#### [NEW] frontend/src/components/Charts/*.jsx
Recharts-based: area chart, bar chart, pie chart, table

#### [NEW] frontend/src/contexts/WebSocketContext.jsx
Singleton WS connection, fan-out to subscribers

---

## Verification Plan

### Automated
1. Start stack: `docker compose up -d`
2. Run simulator: `docker exec slms-agents python log_simulator.py`
3. Check ML pipeline processed logs: `curl http://localhost:8000/api/stats/summary`
4. Browser test: confirm dashboard loads, live stream receives events

### Manual
- Login with admin credentials
- Verify severity badges render correctly
- Confirm charts update in real-time
- Test alert trigger by injecting a Disaster-level event

---

## Open Questions

> [!IMPORTANT]
> **Telegram Bot**: Do you have a Telegram Bot Token and Chat ID? If not, the alerting service will fall back to email-only. You can add these to `.env` later.

> [!NOTE]
> **GeoIP Database**: The MaxMind GeoLite2 database requires a free account. The compose file downloads it automatically if a `MAXMIND_LICENSE_KEY` is set; otherwise GeoIP lookups are skipped gracefully.

> [!NOTE]
> **Log Paths**: On Windows development, the agents mount `/var/log` from the host, which won't exist. The simulator generates synthetic logs so the dashboard is fully functional without a real Ubuntu host.
