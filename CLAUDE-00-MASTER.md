# CLAUDE.md — OpSync Backend: Master Project Context

## Project Overview

**OpSync — Real-Time Restaurant Intelligence** is a real-time decision support system for quick-service restaurant (QSR) managers. It ingests operational data (orders, staffing, inventory), runs demand forecasting and optimization algorithms, and surfaces prioritized recommendations and alerts through a dashboard.

This is a capstone project for CIS 498. The backend is a Python/Flask REST API with SQLAlchemy ORM, JWT authentication, and algorithmic services for demand forecasting, labor optimization, and threshold-based alerting.

## System Name
**OpSync** (short for Operational Sync)

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.12+ / Flask 3.0 |
| ORM | SQLAlchemy 2.0 |
| Database (dev) | SQLite |
| Database (prod) | PostgreSQL 16 |
| Authentication | JWT (Flask-JWT-Extended) |
| Password Hashing | bcrypt |
| ML/Forecasting | scikit-learn, pandas, numpy |
| Task Queue (future) | Celery + Redis |
| Frontend (separate) | React 18 + TypeScript + Recharts |

## Database Tables (7 total)

1. **restaurant** — Physical locations (PK: restaurant_id UUID)
2. **users** — System users with roles (PK: user_id UUID, FK: restaurant_id)
3. **shift** — Operating periods (PK: shift_id UUID, FK: restaurant_id, manager_id)
4. **operational_snapshot** — Time-series metrics captured every 30-60s (PK: snapshot_id UUID, FK: shift_id)
5. **recommendation** — System-generated operational recommendations (PK: recommendation_id UUID, FK: shift_id, snapshot_id)
6. **recommendation_action** — Manager responses to recommendations (PK: action_id UUID, FK: recommendation_id, user_id)
7. **alert** — Threshold-triggered notifications (PK: alert_id UUID, FK: shift_id, snapshot_id)

## User Roles

- **admin**: Full access, system configuration, user management
- **manager**: Dashboard, act on recommendations/alerts, shift management
- **viewer**: Read-only dashboard access

## API Base URL

`http://localhost:5000/api/`

## API Route Groups

| Prefix | Blueprint | Purpose |
|--------|-----------|---------|
| `/api/auth` | auth_bp | Login, register, current user |
| `/api/dashboard` | dashboard_bp | Current state, metrics, trends, evaluate trigger |
| `/api/recommendations` | recommendations_bp | List, detail, act on recommendations |
| `/api/alerts` | alerts_bp | List, acknowledge alerts |
| `/api/restaurants` | restaurants_bp | CRUD (admin only) |
| `/api/shifts` | shifts_bp | List, create, update shifts |

## Three Core Algorithms

1. **Demand Forecasting** (ForecastService) — Weighted moving average predicting order volume by channel for next 15-60 minutes
2. **Labor Optimization** (RecommendationEngine) — Compares predicted demand vs current staffing using configurable ratios, generates prioritized staff reallocation recommendations
3. **Threshold Alerting** (AlertService) — Evaluates snapshots against configurable thresholds (ticket time, queue depth, inventory levels, staffing ratios), generates severity-ranked alerts

## Key Design Decisions

- UUIDs stored as `String(36)` for SQLite compatibility
- `inventory_json` stored as `Text` (JSON string) in SQLite, `JSONB` in PostgreSQL
- Passwords hashed with bcrypt via Flask-Bcrypt
- All timestamps in UTC
- Seed data uses `date.today()` for freshness
- Algorithms use simplified approaches (weighted moving average vs full ARIMA) suitable for MVP

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the dev server
python run.py

# Seed the database
python -m app.seed.seed_data
# OR
flask seed

# Run tests
pytest tests/

# Trigger algorithm evaluation (requires auth token)
curl -X POST http://localhost:5000/api/dashboard/evaluate \
  -H "Authorization: Bearer <token>"
```

## Test Credentials (after seeding)

Each restaurant gets 3 users. Pattern: `{role}@{city}.opsync.com`

| Email | Password | Role | Restaurant |
|-------|----------|------|------------|
| admin@dallas.opsync.com | admin123 | admin | Downtown |
| manager@dallas.opsync.com | manager123 | manager | Downtown |
| viewer@dallas.opsync.com | viewer123 | viewer | Downtown |
| admin@plano.opsync.com | admin123 | admin | Suburban |
| manager@plano.opsync.com | manager123 | manager | Suburban |
| viewer@plano.opsync.com | viewer123 | viewer | Suburban |
| admin@irving.opsync.com | admin123 | admin | Airport |
| manager@irving.opsync.com | manager123 | manager | Airport |
| viewer@irving.opsync.com | viewer123 | viewer | Airport |

---

## Multi-Session Build Order

This project is designed to be built across 5 Claude Code sessions, each with its own CLAUDE.md:

| Session | File | What It Builds | Depends On |
|---------|------|----------------|------------|
| 1 | `CLAUDE-01-PROJECT-SETUP.md` | Project structure, config, app factory, extensions | Nothing |
| 2 | `CLAUDE-02-DATABASE-MODELS.md` | All 7 SQLAlchemy models with full field specs | Session 1 |
| 3 | `CLAUDE-03-API-AUTH.md` | All REST API endpoints, JWT auth, RBAC | Sessions 1-2 |
| 4 | `CLAUDE-04-SEED-DATA.md` | Seed data scripts with realistic restaurant data | Sessions 1-3 |
| 5 | `CLAUDE-05-ALGORITHMS.md` | Forecast, recommendation engine, alert service | Sessions 1-4 |

**Context handoff between sessions**: Each session reads `CLAUDE.md` (this file) + `HANDOFF.md` before starting, and appends its results to `HANDOFF.md` when done. This ensures every session knows exactly what was built before it, including any deviations from the plan.

## Running All Sessions with Claude Code

### Option A: Automated Build Script (Recommended)

Run `./build-opsync.sh` from the `opsync-backend/` directory. The script handles context passing, sequential execution for sessions 1-3, and parallel execution for sessions 4-5. See the script for details.

### Option B: Manual Session-by-Session

```bash
cd opsync-backend

# IMPORTANT: Keep CLAUDE-00-MASTER.md as CLAUDE.md the entire time.
# Each session reads its own instruction file AND CLAUDE.md + HANDOFF.md.
cp CLAUDE-00-MASTER.md CLAUDE.md

# Session 1
claude -p "Read CLAUDE-01-PROJECT-SETUP.md, then CLAUDE.md and HANDOFF.md. Execute all steps in the instruction file. Run verification. Then append your handoff to HANDOFF.md." --allowedTools "Bash,Read,Write,Edit"

# Session 2
claude -p "Read CLAUDE-02-DATABASE-MODELS.md, then CLAUDE.md and HANDOFF.md. Implement all models as specified, but trust HANDOFF.md for actual file paths from Session 1. Run verification. Append handoff." --allowedTools "Bash,Read,Write,Edit"

# Session 3
claude -p "Read CLAUDE-03-API-AUTH.md, then CLAUDE.md and HANDOFF.md. Implement all endpoints. Trust HANDOFF.md for model details from Session 2. Run verification. Append handoff." --allowedTools "Bash,Read,Write,Edit"

# Session 4 (can run in parallel with 5)
claude -p "Read CLAUDE-04-SEED-DATA.md, then CLAUDE.md and HANDOFF.md. Create seed scripts using the actual model structure from HANDOFF.md. Run and verify. Append handoff." --allowedTools "Bash,Read,Write,Edit"

# Session 5 (can run in parallel with 4)
claude -p "Read CLAUDE-05-ALGORITHMS.md, then CLAUDE.md and HANDOFF.md. Implement all algorithm services. Verify against seeded data. Append handoff." --allowedTools "Bash,Read,Write,Edit"
```

### Option C: Using --resume for Chained Context

```bash
cd opsync-backend
cp CLAUDE-00-MASTER.md CLAUDE.md

# Session 1 — starts a named session
claude -p "Read CLAUDE-01-PROJECT-SETUP.md and execute all steps. Append handoff to HANDOFF.md." --allowedTools "Bash,Read,Write,Edit" --session-name "opsync-build"

# Sessions 2-5 — resume the same session (full conversation memory)
claude --resume "opsync-build" -p "Now read CLAUDE-02-DATABASE-MODELS.md and implement all models. Append handoff."
claude --resume "opsync-build" -p "Now read CLAUDE-03-API-AUTH.md and implement all endpoints. Append handoff."
claude --resume "opsync-build" -p "Now read CLAUDE-04-SEED-DATA.md and create seed data. Append handoff."
claude --resume "opsync-build" -p "Now read CLAUDE-05-ALGORITHMS.md and implement algorithms. Append handoff."
```

> **Note**: `--resume` keeps full conversation context so later sessions remember everything earlier sessions did. This is the most reliable approach but uses more context window. HANDOFF.md serves as a backup in case context is trimmed.

## File Structure (Final State)

```
opsync-backend/
├── CLAUDE.md
├── CLAUDE-01-PROJECT-SETUP.md
├── CLAUDE-02-DATABASE-MODELS.md
├── CLAUDE-03-API-AUTH.md
├── CLAUDE-04-SEED-DATA.md
├── CLAUDE-05-ALGORITHMS.md
├── .env.example
├── .gitignore
├── requirements.txt
├── config.py
├── run.py
├── wsgi.py
├── app/
│   ├── __init__.py
│   ├── extensions.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── restaurant.py
│   │   ├── user.py
│   │   ├── shift.py
│   │   ├── operational_snapshot.py
│   │   ├── recommendation.py
│   │   ├── recommendation_action.py
│   │   └── alert.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── dashboard.py
│   │   ├── recommendations.py
│   │   ├── alerts.py
│   │   ├── restaurants.py
│   │   └── shifts.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── dashboard_service.py
│   │   ├── recommendation_engine.py
│   │   ├── alert_service.py
│   │   └── forecast_service.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── decorators.py
│   │   ├── errors.py
│   │   └── helpers.py
│   └── seed/
│       ├── __init__.py
│       └── seed_data.py
├── migrations/
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_auth.py
    ├── test_dashboard.py
    └── test_models.py
```
