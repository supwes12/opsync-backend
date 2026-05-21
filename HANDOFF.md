# HANDOFF.md — OpSync Build State

> **This file is the single source of truth for what has been built.**
> Every session MUST read this before starting work, and MUST append its handoff section after completing.

---

## How This Works

Each build session follows this protocol:

1. **READ** `CLAUDE.md` (master project context)
2. **READ** `HANDOFF.md` (this file — what's been built so far)
3. **DO** the work described in your session instruction file
4. **APPEND** your handoff section to this file using the template below

If a previous session made any deviations from the plan (renamed a file, changed an import path, added an extra dependency), it will be documented here. **Always trust HANDOFF.md over the instruction file when they conflict** — the handoff reflects what actually exists on disk.

---

## Handoff Template

When you finish your session, append a section like this:

```markdown
---

## Session X: [Name] — COMPLETED

**Completed by**: Claude Code Session X
**Timestamp**: [ISO timestamp]

### What Was Built
- [ list every file created or modified, with full paths ]

### Key Decisions & Deviations
- [ anything that differs from the instruction file ]
- [ naming changes, extra files, workarounds ]
- "None" if everything matched the plan exactly

### Dependencies Installed
- [ any packages added beyond requirements.txt ]
- "None" if requirements.txt was unchanged

### Verification Results
- [ paste or summarize the output of verification checks ]
- [ any tests that passed/failed ]

### What The Next Session Needs to Know
- [ critical info: actual file paths, class names, import patterns ]
- [ any gotchas or things that work differently than expected ]
- [ database state: was db.create_all() run? are tables populated? ]

### Files Created/Modified (Full Manifest)
\```
path/to/file1.py — [created | modified] — [one-line description]
path/to/file2.py — [created | modified] — [one-line description]
\```
```

---

## Current Build State

**Session 1 completed.** Sessions 2-5 remain.

The sections below are populated as each session runs.

## Session 1: Project Setup & Environment Configuration — COMPLETED

**Completed by**: Claude Code Session 1
**Timestamp**: 2026-05-13T00:00:00Z

### What Was Built
- Complete Flask project skeleton with app factory pattern
- Configuration hierarchy (dev/test/prod) with SQLite default and PostgreSQL swap via env var
- All Flask extensions initialized (SQLAlchemy, Migrate, JWT, Bcrypt, CORS)
- Blueprint registration for all 6 API route groups
- Error handlers (400, 401, 403, 404, 500)
- Role-based access decorator (`role_required`)
- UUID/datetime utility helpers
- Placeholder stubs for all models, API routes, services, and seed data
- Test infrastructure with pytest fixtures (conftest.py)
- Virtual environment created at `venv/`

### Key Decisions & Deviations
- Created a virtual environment (`venv/`) because the system Python (3.14.4 via Homebrew) is externally managed (PEP 668). All future sessions must activate it: `source venv/bin/activate`
- Python version is 3.14.4 (higher than the 3.12+ requirement — fully compatible)
- Port 5000 is occupied by macOS AirPlay Receiver. Use `app.run(port=5001)` or disable AirPlay Receiver in System Settings if you need to run the dev server directly
- SQLite database is created at `instance/opsync_dev.db` (Flask's default instance path), not project root

### Dependencies Installed
- All packages from requirements.txt installed successfully in venv

### Verification Results
- `pip install -r requirements.txt` — SUCCESS
- `python -c "from app import create_app; app = create_app('testing'); print('OK')"` — SUCCESS (prints "OK")
- All 7 `__init__.py` files verified present
- SQLite database file created at `instance/opsync_dev.db` on `db.create_all()`
- `pytest tests/ -v` — 3/3 placeholder tests PASSED
- Flask routing verified via test client (405 on GET /api/auth/login confirms routing works)

### What The Next Session Needs to Know
- **Activate venv first**: `cd opsync-backend && source venv/bin/activate`
- **Import pattern for models**: `from app.models import Restaurant, User, Shift, ...` (all re-exported from `app/models/__init__.py`)
- **Import pattern for extensions**: `from app.extensions import db, bcrypt, jwt, ...`
- **Model stubs**: Each model file has `class ModelName(db.Model)` with `__tablename__` and `pass` — Session 2 needs to replace `pass` with full column definitions
- **API stubs**: Each blueprint file has the blueprint object and route functions with `raise NotImplementedError` — Session 3 replaces these
- **DB location**: `instance/opsync_dev.db` (SQLite)
- **Config access**: `from config import config_by_name` then `config_by_name['development']`, etc.

### Files Created/Modified (Full Manifest)
```
.env.example — created — Template environment variables
.gitignore — created — Python/Flask gitignore
requirements.txt — created — Pinned dependencies (18 packages)
config.py — created — App configuration classes (Dev/Test/Prod)
run.py — created — Application entry point
wsgi.py — created — WSGI entry point for production
app/__init__.py — created — Flask app factory (create_app)
app/extensions.py — created — SQLAlchemy, Migrate, JWT, Bcrypt, CORS init
app/models/__init__.py — created — Model re-exports
app/models/restaurant.py — created — Restaurant model stub
app/models/user.py — created — User model stub
app/models/shift.py — created — Shift model stub
app/models/operational_snapshot.py — created — OperationalSnapshot model stub
app/models/recommendation.py — created — Recommendation model stub
app/models/recommendation_action.py — created — RecommendationAction model stub
app/models/alert.py — created — Alert model stub
app/api/__init__.py — created — Blueprint registration (register_blueprints)
app/api/auth.py — created — Auth blueprint with placeholder routes
app/api/dashboard.py — created — Dashboard blueprint with placeholder routes
app/api/recommendations.py — created — Recommendations blueprint with placeholder routes
app/api/alerts.py — created — Alerts blueprint with placeholder routes
app/api/restaurants.py — created — Restaurants blueprint with placeholder routes
app/api/shifts.py — created — Shifts blueprint with placeholder routes
app/services/__init__.py — created — Empty package init
app/services/auth_service.py — created — AuthService stub
app/services/dashboard_service.py — created — DashboardService stub
app/services/recommendation_engine.py — created — RecommendationEngine stub
app/services/alert_service.py — created — AlertService stub
app/services/forecast_service.py — created — ForecastService stub
app/utils/__init__.py — created — Empty package init
app/utils/errors.py — created — Error handlers (400-500)
app/utils/decorators.py — created — role_required decorator
app/utils/helpers.py — created — generate_uuid, utc_now helpers
app/seed/__init__.py — created — Empty package init
app/seed/seed_data.py — created — Seed script stub
tests/__init__.py — created — Empty package init
tests/conftest.py — created — Pytest fixtures (app, db, client)
tests/test_auth.py — created — Placeholder test
tests/test_dashboard.py — created — Placeholder test
tests/test_models.py — created — Placeholder test
```

<!-- SESSION 1 HANDOFF GOES HERE -->

## Session 2: Database Schema & SQLAlchemy Models — COMPLETED

**Completed by**: Claude Code Session 2
**Timestamp**: 2026-05-13T20:55:00Z

### What Was Built
- All 7 SQLAlchemy ORM models with full column definitions, relationships, and `to_dict()` methods
- UUID primary keys using `String(36)` with `generate_uuid` from `app/utils/helpers.py`
- Password hashing via `set_password()` / `check_password()` using Flask-Bcrypt from extensions
- `OperationalSnapshot.inventory` property (getter/setter) for JSON serialization of `inventory_json`
- Added model import in app factory (`from app import models`) so `db.create_all()` works

### Key Decisions & Deviations
- Added `from app import models` to `app/__init__.py` inside `create_app()` — Session 1's stubs were only imported inside the shell context processor, so `db.create_all()` produced 0 tables without this fix
- Used `lazy='dynamic'` on all one-to-many relationships (returns query objects, not lists — use `.all()` or `.count()`)
- `datetime.utcnow` used for defaults as specified (Python 3.14 shows deprecation warnings but it works fine)
- `generate_uuid` imported from `app.utils.helpers` (reusing Session 1's helper) rather than defining locally in each model

### Dependencies Installed
- None — all required packages were already in requirements.txt

### Verification Results
- `db.create_all()` creates all 7 tables: `alert`, `operational_snapshot`, `recommendation`, `recommendation_action`, `restaurant`, `shift`, `users`
- All relationships verified bidirectionally (restaurant↔users, restaurant↔shifts, shift↔snapshots, shift↔recommendations, shift↔alerts, snapshot↔recommendations, snapshot↔alerts, recommendation↔actions, user↔recommendation_actions, user↔managed_shifts, user↔acknowledged_alerts)
- `to_dict()` verified on all models — returns JSON-serializable dicts
- `User.set_password()` / `check_password()` verified with bcrypt
- `password_hash` confirmed excluded from `User.to_dict()`
- `OperationalSnapshot.inventory` property getter/setter verified (JSON round-trip)
- `pytest tests/ -v` — 3/3 tests PASSED
- Dev database created at `instance/opsync_dev.db` with all 7 tables

### What The Next Session Needs to Know

**Model import pattern**: `from app.models import Restaurant, User, Shift, OperationalSnapshot, Recommendation, RecommendationAction, Alert`

**Table names (for FK references)**:
- `restaurant` (PK: `restaurant_id`)
- `users` (PK: `user_id`) — plural because `user` is reserved
- `shift` (PK: `shift_id`)
- `operational_snapshot` (PK: `snapshot_id`)
- `recommendation` (PK: `recommendation_id`)
- `recommendation_action` (PK: `action_id`)
- `alert` (PK: `alert_id`)

**Relationship names (backrefs available on related models)**:
- `Restaurant.shifts`, `Restaurant.users`
- `User.recommendation_actions`, `User.managed_shifts`, `User.acknowledged_alerts`
- `Shift.snapshots`, `Shift.recommendations`, `Shift.alerts`
- `Shift.restaurant` (backref), `Shift.manager` (backref)
- `OperationalSnapshot.shift` (backref), `OperationalSnapshot.recommendations`, `OperationalSnapshot.alerts`
- `Recommendation.shift` (backref), `Recommendation.snapshot` (backref), `Recommendation.actions`
- `RecommendationAction.recommendation` (backref), `RecommendationAction.user` (backref)
- `Alert.shift` (backref), `Alert.snapshot` (backref), `Alert.acknowledger` (backref)

**All relationships use `lazy='dynamic'`** — returns query objects. Use `.all()` for lists, `.count()` for count, `.filter()` for filtering.

**Password methods on User**:
- `user.set_password('plaintext')` — hashes and stores in `password_hash`
- `user.check_password('plaintext')` — returns `True`/`False`

**Snapshot inventory**:
- `snapshot.inventory = {'buns': 200}` — setter auto-serializes to JSON string
- `snapshot.inventory` — getter auto-deserializes from JSON string

**Database state**: `instance/opsync_dev.db` exists with all 7 tables but no data rows. Session 4 (seed data) will populate it.

### Files Created/Modified (Full Manifest)
```
app/__init__.py — modified — Added 'from app import models' inside create_app() for table registration
app/models/__init__.py — modified — Added __all__ export list
app/models/restaurant.py — modified — Full model: 10 columns, 2 relationships, to_dict(), __repr__()
app/models/user.py — modified — Full model: 9 columns, 3 relationships, set_password(), check_password(), to_dict(), __repr__()
app/models/shift.py — modified — Full model: 8 columns, 3 relationships, to_dict() with manager name, __repr__()
app/models/operational_snapshot.py — modified — Full model: 13 columns, 2 relationships, inventory property, to_dict(), __repr__()
app/models/recommendation.py — modified — Full model: 11 columns, 1 relationship, to_dict(), __repr__()
app/models/recommendation_action.py — modified — Full model: 6 columns, to_dict() with user name, __repr__()
app/models/alert.py — modified — Full model: 10 columns, to_dict(), __repr__()
```

<!-- SESSION 2 HANDOFF GOES HERE -->

## Session 3: REST API Endpoints & JWT Authentication — COMPLETED

**Completed by**: Claude Code Session 3
**Timestamp**: 2026-05-13T21:30:00Z

### What Was Built
- Complete REST API with 19 endpoints across 6 blueprints
- JWT authentication with role-based access control (RBAC)
- Service layer (AuthService, DashboardService) separating business logic from routes
- `role_required` decorator (from Session 1) used for RBAC on admin/manager-only endpoints
- 17 pytest tests covering auth, dashboard, and model behavior

### All API Endpoints

| Method | Path | Auth | Roles | Description |
|--------|------|------|-------|-------------|
| POST | `/api/auth/register` | No | Public | Register a new user |
| POST | `/api/auth/login` | No | Public | Login, returns JWT |
| GET | `/api/auth/me` | Yes | Any | Get current user info |
| GET | `/api/dashboard/current` | Yes | Any | Current shift, snapshot, recs, alerts |
| GET | `/api/dashboard/metrics` | Yes | Any | Time-series snapshots for a shift |
| GET | `/api/dashboard/trends` | Yes | Any | Daily aggregates over N days |
| POST | `/api/dashboard/evaluate` | Yes | Any | Trigger algorithm evaluation (stub for Session 5) |
| GET | `/api/recommendations/` | Yes | Any | List recommendations for a shift |
| GET | `/api/recommendations/<id>` | Yes | Any | Single recommendation with actions |
| POST | `/api/recommendations/<id>/action` | Yes | admin, manager | Accept/defer/reject a recommendation |
| GET | `/api/alerts/` | Yes | Any | List alerts for a shift |
| PUT | `/api/alerts/<id>/acknowledge` | Yes | admin, manager | Acknowledge an alert |
| GET | `/api/restaurants/` | Yes | admin | List all restaurants |
| GET | `/api/restaurants/<id>` | Yes | Any (own) / admin (all) | Get single restaurant |
| POST | `/api/restaurants/` | Yes | admin | Create restaurant |
| PUT | `/api/restaurants/<id>` | Yes | admin | Update restaurant |
| DELETE | `/api/restaurants/<id>` | Yes | admin | Delete restaurant |
| GET | `/api/shifts/` | Yes | Any | List shifts (filtered by restaurant, status, date) |
| GET | `/api/shifts/<id>` | Yes | Any | Single shift with snapshot/rec counts |
| POST | `/api/shifts/` | Yes | admin, manager | Create a shift |
| PUT | `/api/shifts/<id>` | Yes | admin, manager | Update shift status/fields |

### JWT Claims Structure

```python
# Token identity: user.user_id (string UUID)
# Additional claims:
{
    'email': 'user@example.com',
    'role': 'admin' | 'manager' | 'viewer',
    'restaurant_id': 'uuid-string'
}
```

**Access in endpoints**:
```python
from flask_jwt_extended import get_jwt_identity, get_jwt
user_id = get_jwt_identity()        # returns user_id string
claims = get_jwt()                  # returns dict with email, role, restaurant_id
role = claims.get('role')
restaurant_id = claims.get('restaurant_id')
```

### Working Curl Login Example

```bash
# Login
curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"curltest@test.com","password":"test123"}'

# Use the returned access_token:
curl http://localhost:5001/api/auth/me \
  -H "Authorization: Bearer <paste_token_here>"
```

### Key Decisions & Deviations
- Alert acknowledge uses `PUT` (not `POST` from Session 1 stub) — matches REST semantics for updating a resource
- Added `GET /api/shifts/<shift_id>` endpoint (Session 1 stub didn't include it) — returns shift with `snapshot_count` and `recommendation_count`
- Added `GET /api/dashboard/metrics` and `GET /api/dashboard/trends` endpoints (Session 1 stub only had `/current` and `/evaluate`)
- `POST /api/dashboard/evaluate` is a stub returning `{'message': 'Evaluation triggered'}` — Session 5 will wire it to the algorithm services
- Used `db.session.get(Model, pk)` for primary key lookups (modern SQLAlchemy 2.0 pattern)
- Priority/severity sorting uses `sqlalchemy.case()` for proper ordering (high > medium > low, critical > warning > info)
- Service layer returns `{'error': ..., 'status_code': ...}` on failure, which API routes translate to HTTP responses

### Dependencies Installed
- None — all required packages were already in requirements.txt

### Verification Results
- `pytest tests/ -v` — **17/17 tests PASSED**
  - test_auth.py: 10 tests (register success/duplicate/missing/invalid role, login success/wrong pw/nonexistent/missing, me with/without token)
  - test_dashboard.py: 5 tests (no active shift 404, active shift returns data, requires auth, metrics requires shift_id, metrics returns snapshots)
  - test_models.py: 2 tests (password hashing, to_dict excludes password_hash)
- Smoke test: login → get token → /me → dashboard (404 no shift) → restaurants list → shifts list — all correct status codes
- RBAC verified: viewer cannot POST to `/api/recommendations/<id>/action` (returns 403)

### What The Next Session Needs to Know

**Authentication for API calls** (Sessions 4 & 5):
1. POST to `/api/auth/login` with `{"email": "...", "password": "..."}` → get `access_token`
2. Include `Authorization: Bearer <token>` header on all protected routes
3. The token contains `user_id` as identity, plus `email`, `role`, `restaurant_id` as claims

**Service imports**:
- `from app.services.auth_service import AuthService`
- `from app.services.dashboard_service import DashboardService`

**Session 5 — Algorithm integration points**:
- `POST /api/dashboard/evaluate` is the trigger endpoint (currently a stub) — wire it to call ForecastService, RecommendationEngine, AlertService
- Recommendations are created by the engine and stored via `db.session.add(Recommendation(...))` → the API already handles listing/acting on them
- Alerts are created by AlertService and stored via `db.session.add(Alert(...))` → the API already handles listing/acknowledging them

**Database state**: `instance/opsync_dev.db` has 7 tables with 1 test restaurant and 1 test user. Session 4 should either clear and reseed or append.

**Port note**: macOS AirPlay Receiver uses port 5000. Use port 5001 for dev server (`python run.py` may need updating or use `flask run -p 5001`).

### Files Created/Modified (Full Manifest)
```
app/services/auth_service.py — modified — Full AuthService: register_user, login_user, get_current_user
app/services/dashboard_service.py — modified — Full DashboardService: get_current_dashboard, get_shift_metrics, get_trends
app/api/auth.py — modified — Auth endpoints: POST /register, POST /login, GET /me
app/api/dashboard.py — modified — Dashboard endpoints: GET /current, GET /metrics, GET /trends, POST /evaluate
app/api/recommendations.py — modified — Recommendation endpoints: GET /, GET /<id>, POST /<id>/action
app/api/alerts.py — modified — Alert endpoints: GET /, PUT /<id>/acknowledge
app/api/restaurants.py — modified — Restaurant CRUD: GET /, GET /<id>, POST /, PUT /<id>, DELETE /<id>
app/api/shifts.py — modified — Shift endpoints: GET /, GET /<id>, POST /, PUT /<id>
tests/conftest.py — modified — Updated fixtures: sample_restaurant, sample_user, admin_user, auth_headers, admin_headers, autouse cleanup
tests/test_auth.py — modified — 10 auth tests (register, login, /me)
tests/test_dashboard.py — modified — 5 dashboard tests (current, metrics)
tests/test_models.py — modified — 2 model tests (password hashing, to_dict)
```

<!-- SESSION 3 HANDOFF COMPLETE -->

## Session 4: Seed Data Scripts — COMPLETED

**Completed by**: Claude Code Session 4
**Timestamp**: 2026-05-13T22:00:00Z

### What Was Built
- Complete seed data script (`app/seed/seed_data.py`) with realistic, interconnected restaurant operational data
- Flask CLI command (`flask seed`) registered in `app/__init__.py`
- `.flaskenv` file to set `FLASK_APP=run.py` so `flask seed` uses development config
- 7 seed functions covering all database tables in correct dependency order
- Idempotent: clears all data before re-seeding

### Record Counts

| Table | Count |
|-------|-------|
| Restaurant | 3 |
| Users | 9 |
| Shift | 7 (3 Downtown, 2 Plano, 2 Irving) |
| OperationalSnapshot | 70 (10 morning + 36 lunch + 24 other active shifts) |
| Recommendation | 10 |
| RecommendationAction | 5 |
| Alert | 7 |

### Test Credentials

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

### Key IDs (regenerated on each seed — use queries, not hardcoded IDs)

**Note**: UUIDs change every re-seed because `generate_uuid` creates fresh UUIDs. Session 5 should query by attributes (e.g., `Shift.query.filter_by(status='active', shift_type='lunch')`) rather than hardcoding IDs.

**Active Shifts** (4 total):
- Dallas lunch (shift_type='lunch', status='active', Downtown restaurant)
- Dallas dinner (shift_type='dinner', status='active', Downtown restaurant)
- Plano lunch (shift_type='lunch', status='active', Suburban restaurant)
- Irving lunch (shift_type='lunch', status='active', Airport restaurant)

**Completed Shifts** (3 total):
- Dallas morning, Plano morning, Irving morning

**Snapshot Time Range**: today 07:00 → today 17:45 (uses `date.today()` so always current)

**Downtown Lunch Snapshots** (36 total, 5-min intervals 11:00–13:55):
- Ramp-up (11:00–11:55): orders 5→35, ticket 90→140s, staff 6
- Peak (12:00–12:55): orders 40→55, ticket 150→240s, staff 6
- Cool-down (13:00–13:55): orders 30→20, ticket 130→100s, staff 5

### Key Decisions & Deviations
- Created `.flaskenv` with `FLASK_APP=run.py` — without this, Flask CLI auto-discovers `wsgi.py` which uses production config (no DATABASE_URL set → crash)
- 7 shifts instead of 9 — instructions said "9 records (3 per restaurant)" but then specified 3 for Downtown and "at least one active" for the other two. Created 3+2+2=7 to match the detailed spec.
- Used `random.seed(42)` for reproducible-ish results, but UUIDs are still random (generated by `uuid.uuid4()` in the model default)
- Recommendation `is_active` states updated by `seed_recommendation_actions()` — accepted/rejected recommendations get `is_active = False`

### Dependencies Installed
- None

### Verification Results
- `python -m app.seed.seed_data` — SUCCESS, all counts printed
- `flask seed` — SUCCESS (after adding `.flaskenv`)
- Idempotent: ran seed twice, counts identical both times
- Login verified: `admin@dallas.opsync.com` / `admin123` → `check_password()` returns True
- `manager@dallas.opsync.com` / `manager123` → True
- Inventory JSON round-trip verified: dict with 8 items parses correctly
- `pytest tests/ -v` — **17/17 tests PASSED**

### What The Next Session Needs to Know

**How to run seed**:
```bash
cd opsync-backend && source venv/bin/activate
python -m app.seed.seed_data
# OR
flask seed
```

**Querying seeded data for algorithm evaluation** (Session 5):
```python
# Get active lunch shift for Downtown
from app.models import Shift, Restaurant
downtown = Restaurant.query.filter_by(city='Dallas').first()
lunch_shift = Shift.query.filter_by(
    restaurant_id=downtown.restaurant_id,
    shift_type='lunch',
    status='active'
).first()

# Get snapshots for that shift (ordered by time)
snapshots = lunch_shift.snapshots.order_by(OperationalSnapshot.captured_at.asc()).all()

# Get latest snapshot
latest = lunch_shift.snapshots.order_by(OperationalSnapshot.captured_at.desc()).first()
```

**Snapshot data shape**: Each snapshot has `total_orders`, `dine_in_orders`, `drive_thru_orders`, `pickup_orders`, `delivery_orders`, `avg_ticket_time_sec`, `staff_count`, `kitchen_staff`, `front_staff`, and `inventory` (property that auto-parses `inventory_json`).

**Inventory format**: `{"item_name": {"current": int, "par": int, "unit": str}, ...}` — 8 items per snapshot.

**Port reminder**: macOS AirPlay uses port 5000. Dev server runs on port 5001 or disable AirPlay.

### Files Created/Modified (Full Manifest)
```
app/seed/seed_data.py — modified — Complete seed script: 7 tables, realistic time-series data, idempotent
app/__init__.py — modified — Added `flask seed` CLI command
.flaskenv — created — Sets FLASK_APP=run.py and FLASK_ENV=development for Flask CLI
```

<!-- SESSION 4 HANDOFF COMPLETE -->

## Session 5: Algorithms & Recommendation Engine — COMPLETED

**Completed by**: Claude Code Session 5
**Timestamp**: 2026-05-13T21:15:00Z

### What Was Built
- **ForecastService** — Weighted moving average demand forecasting with trend detection (linear regression), confidence levels, and horizon scaling
- **RecommendationEngine** — Labor optimization (kitchen/front staffing vs demand), inventory monitoring (critical/warning thresholds), prep timing for next shift, deduplication, and max-active-recs enforcement
- **AlertService** — Ticket time alerts (warning at 180s, critical at 300s), queue surge detection (150% of 30-min trailing avg), inventory stockout risk, labor imbalance detection, auto-resolve for cleared conditions, and max-active-alerts enforcement
- **Evaluate endpoint** — Wired `POST /api/dashboard/evaluate` to call all three services sequentially and return combined results

### Key Decisions & Deviations
- MVP simplification: alerts are created immediately without the 2-snapshot persistence state machine described in the design doc. A code comment documents the production behavior.
- Auto-resolve logic: active alerts whose triggering condition is no longer present in the current snapshot are automatically acknowledged (system-resolved).
- Trend calculation uses simple linear regression normalized to a 0.8–1.3 multiplier range.
- `orders_per_hour` in RecommendationEngine is estimated as `predicted_total_orders * 2` (since the 30-min forecast covers half an hour).
- Inventory items must be dicts with `current`, `par`, and `unit` keys — the seed data from Session 4 already uses this format.
- The evaluate endpoint does not require `admin` or `manager` role (matches Session 3's implementation where all authenticated users can trigger it).

### Dependencies Installed
- None — all required packages were already in requirements.txt

### Verification Results
- **ForecastService**: Predicted 20 total orders (high confidence) from 5 snapshots with correct channel breakdown
- **RecommendationEngine**: Generated 2 inventory_warning recommendations on first run, 0 on second run (deduplication confirmed)
- **AlertService**: Generated ticket_time_warning and labor_imbalance alerts on high-stress snapshots (ticket_time=230s, orders/kitchen ratio=16.7:1)
- **Evaluate endpoint**: Returns 200 with `forecast`, `new_recommendations`, and `new_alerts` fields
- **Deduplication**: Running evaluate twice on the same snapshot produces 0 duplicate recommendations
- **pytest tests/ -v**: 17/17 tests PASSED (all existing tests remain green)

### Algorithm Details

**ForecastService.forecast_demand(shift_id, horizon_minutes=30)**
- Weights: [0.35, 0.25, 0.20, 0.12, 0.08] for last 5 snapshots
- Confidence: high (5+ snapshots), medium (3-4), low (<3)
- Returns: `predicted_total_orders`, `predicted_by_channel` (dine_in, drive_thru, pickup, delivery), `predicted_avg_ticket_time`, `confidence`, `horizon_minutes`, `generated_at`

**RecommendationEngine.evaluate(shift_id, snapshot_id)**
- Staffing ratios: KITCHEN_RATIO=8, FRONT_RATIO=12 (orders per staff per hour)
- Inventory thresholds: CRITICAL=15%, WARNING=30% of par
- Priority formula: (gap_magnitude * 0.4) + (demand_duration * 0.3) + (ticket_impact * 0.3)
- Max 5 active recommendations per shift
- Returns: list of Recommendation model objects

**AlertService.evaluate(shift_id, snapshot_id)**
- Thresholds: ticket_time warning=180s, critical=300s; queue_surge=150%; inventory_critical=20%; kitchen_ratio=10:1, front_ratio=15:1
- Max 5 active alerts per shift
- Auto-resolves alerts when condition clears
- Returns: list of Alert model objects

### What The Next Session Needs to Know
- This is the final session — the project build is complete
- All three algorithm services are importable: `from app.services.forecast_service import ForecastService`, `from app.services.recommendation_engine import RecommendationEngine`, `from app.services.alert_service import AlertService`
- The evaluate endpoint is fully wired: `POST /api/dashboard/evaluate` (requires JWT auth)
- Database state after algorithms ran: 12 recommendations and 9 alerts total (includes Session 4's seed data + algorithm-generated records)
- All thresholds are class-level constants and easily configurable

### Files Created/Modified (Full Manifest)
```
app/services/forecast_service.py — modified — Full ForecastService: forecast_demand, _calculate_trend
app/services/recommendation_engine.py — modified — Full RecommendationEngine: evaluate, _check_labor, _check_inventory, _check_prep_timing, _calculate_priority, _deduplicate
app/services/alert_service.py — modified — Full AlertService: evaluate, _check_ticket_time, _check_queue_surge, _check_inventory_levels, _check_labor_balance, _auto_resolve, _enforce_max_alerts
app/api/dashboard.py — modified — Wired POST /evaluate to call ForecastService, RecommendationEngine, AlertService
```

<!-- SESSION 5 HANDOFF COMPLETE -->
