# GoEye - Network Analytics Dashboard

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Vercel-black?style=for-the-badge&logo=vercel)](https://goeye-dashboard.vercel.app)
[![Backend](https://img.shields.io/badge/API-Render-46E3B7?style=for-the-badge&logo=render)](https://goeye-backend.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://neon.tech)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

A full-stack **Quality of Service (QoS) analytics platform** built for Go Telecom (Saudi Arabia). GoEye aggregates network measurement data from subscriber-premises units and surfaces it through an interactive analytics dashboard which covers gaming latency, social media responsiveness, video conferencing quality, CDN performance, and DNS reliability across multiple operator scopes.

> **Portfolio note:** This public version runs entirely on synthetic seeded data. No SamKnows credentials or real subscriber data are included.

---

## Live Demo

| URL | Credentials |
|-----|-------------|
| [goeye-dashboard.vercel.app](https://goeye-dashboard.vercel.app) | Username: `demo` · Password: `demo1234` |

> The backend is hosted on Render's free tier and may take ~30 seconds to wake from cold start on first login.

---

## Features

- **JWT Authentication** - role-based access with 8-hour session tokens; credentials never stored in localStorage
- **Multi-scope comparison** - side-by-side KPI comparison across operator/technology segments (GO/FTTH, GO/B2B, KSA Average)
- **Gaming latency tracking** - per-game RTT trends for 28 titles (Valorant, League of Legends, PUBG, and more)
- **Social media breakdown** - per-platform latency with CDN vs. origin endpoint distinction
- **Video conferencing quality** - RTT analysis across conferencing platforms
- **DNS performance** - resolver response-time detail
- **Disconnection monitoring** - reliability heatmap by hour of day
- **Date range picker** - load any single date or a custom range from the DB; union with live server dates when pipeline is active
- **Trend analysis** - 30-day rolling trends per scope
- **ETL pipeline** - production-ready downloader → extractor → parser → aggregator pipeline (SamKnows-compatible, dormant in demo mode)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Vite, Recharts, react-heatmap-grid, Axios |
| Backend | FastAPI, SQLAlchemy 2, python-jose (JWT), passlib (bcrypt) |
| Database | PostgreSQL 16 (Neon serverless in production) |
| Pipeline | pandas, NumPy, BeautifulSoup4, requests |
| Hosting | Vercel (frontend) · Render (backend) · Neon (database) |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        Browser                          │
│              React 19 + Vite (Vercel)                   │
└──────────────────────┬──────────────────────────────────┘
                       │  HTTPS / JWT in Authorization header
┌──────────────────────▼──────────────────────────────────┐
│               FastAPI Backend (Render)                   │
│  /auth/login   /api/daily   /api/hourly                 │
│  /api/gaming/breakdown      /api/social/breakdown        │
│  /api/available-dates       /api/loaded-dates            │
└──────────────────────┬──────────────────────────────────┘
                       │  SQLAlchemy ORM
┌──────────────────────▼──────────────────────────────────┐
│             PostgreSQL - Neon (cloud)                    │
│  units · scopes · scope_units · applications            │
│  daily_aggregates · hourly_aggregates                   │
│  raw_game_latency · raw_social_media                    │
│  raw_video_conferencing · raw_dns · users               │
└─────────────────────────────────────────────────────────┘

Optional (production pipeline - not active in demo):
┌─────────────────────────────────────────────────────────┐
│  SamKnows Measurement Server                            │
│  downloader → extractor → parsers → aggregators         │
│  Scheduled nightly via Windows Task Scheduler           │
└─────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
gonet-dashboard-v1-portfolio/
├── api/
│   └── main.py                  # FastAPI app - all endpoints
├── models/                      # SQLAlchemy ORM models
│   ├── units.py
│   ├── scopes.py
│   ├── scope_units.py
│   ├── applications.py
│   ├── daily_aggregates.py
│   ├── hourly_aggregates.py
│   ├── raw_game_latency.py
│   ├── raw_social_media.py
│   ├── raw_video_conferencing.py
│   ├── raw_dns.py
│   └── users.py
├── pipeline/                    # ETL pipeline (dormant in demo)
│   ├── downloader.py
│   ├── extractor.py
│   ├── run_pipeline.py
│   └── parsers/
├── frontend/
│   ├── src/
│   │   ├── api/client.js        # Axios client + interceptors
│   │   ├── pages/
│   │   │   ├── Login.jsx
│   │   │   └── Dashboard.jsx
│   │   └── components/
│   │       ├── Sidebar.jsx
│   │       ├── KPICard.jsx
│   │       ├── Panel.jsx
│   │       ├── HeatmapPanel.jsx
│   │       ├── ReliabilityChart.jsx
│   │       ├── ComparisonTable.jsx
│   │       └── InsightsPanel.jsx
│   └── package.json
├── database.py                  # SQLAlchemy engine (DATABASE_URL or individual vars)
├── create_tables.py             # Schema creation script
├── load_reference_data.py       # Seed units, scopes, applications
├── seed_demo_data.py            # 14 days of synthetic QoS data
├── create_user.py               # User account creation utility
├── requirements.txt
├── Procfile                     # Render start command
└── .env.example                 # Environment variable reference
```

---

## Local Development

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 14+ (or a free [Neon](https://neon.tech) project)

### 1. Clone and configure

```bash
git clone https://github.com/YOUR_USERNAME/gonet-dashboard-v1-portfolio.git
cd gonet-dashboard-v1-portfolio

cp .env.example .env
# Edit .env - fill in your DB connection details and generate a JWT_SECRET
```

Generate a JWT secret:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Backend

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1      # Windows
# source venv/bin/activate       # macOS / Linux

pip install -r requirements.txt

python create_tables.py
python load_reference_data.py    # requires Units_Data.csv in project root
python seed_demo_data.py
python create_user.py

uvicorn api.main:app --reload --port 8001
```

API is available at `http://localhost:8001` - interactive docs at `/docs`.

### 3. Frontend

```bash
cd frontend
npm install
# Create frontend/.env.local with:
# VITE_API_URL=http://localhost:8001
npm run dev
```

Dashboard opens at `http://localhost:5173`.

---

## Deployment

The stack deploys entirely on free tiers:

| Service | Purpose | Free tier limits |
|---------|---------|-----------------|
| [Neon](https://neon.tech) | PostgreSQL database | 512 MB storage, 1 project |
| [Render](https://render.com) | FastAPI backend | 750 hrs/month, cold-starts after 15 min inactivity |
| [Vercel](https://vercel.com) | React frontend | Unlimited deployments |

See [`.env.example`](.env.example) for all required environment variables.

**Render environment variables required:**
- `DATABASE_URL` - Neon connection string
- `JWT_SECRET` - 32+ character random string

**Vercel environment variable required:**
- `VITE_API_URL` - your Render backend URL

---

## License

[MIT](LICENSE) - Ahmed Hassnain, 2026
