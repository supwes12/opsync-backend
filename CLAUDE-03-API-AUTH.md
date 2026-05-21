# CLAUDE.md — Session 3: REST API Endpoints & JWT Authentication

## BEFORE YOU START — Context Protocol

1. **Read `CLAUDE.md`** (the master project context file in this directory)
2. **Read `HANDOFF.md`** — Sessions 1 and 2 should have documented what they built. Pay special attention to:
   - The exact model class names and `to_dict()` method signatures from Session 2
   - The actual import paths (e.g., `from app.models import User`)
   - Any column name differences or relationship names
3. **Use what's actually on disk**, not what this instruction file assumes. If Session 2's handoff says a field is named differently, use that name.
4. Verify the models work: run `python -c "from app.models import *; print('Models OK')"` before writing any API code.
5. Then proceed with the work below.

## WHEN YOU FINISH — Handoff Protocol

After completing all steps and verification:
1. **Append your handoff section to `HANDOFF.md`** using the template defined in that file
2. Include: every endpoint implemented (method + path), the blueprint registration, any middleware or decorators created, and test results
3. Document the exact JWT claims structure you implemented (Sessions 4 and 5 need to know how to authenticate)
4. Include a working curl example for login that returns a real token
5. This is **mandatory** — Sessions 4 and 5 need to know the API surface

---

## Mission

Implement all REST API endpoints for the OpSync backend, including JWT-based authentication with role-based access control (RBAC), dashboard data retrieval, recommendation management, alert handling, and CRUD operations for restaurants and shifts.

## Prerequisites

Sessions 1 and 2 must be complete:
- Flask project structure exists and runs
- All 7 SQLAlchemy models are implemented with `to_dict()` methods
- `app/extensions.py` has `db`, `jwt`, `bcrypt` initialized
- `app/utils/decorators.py` has `role_required` decorator
- SQLite database creates all 7 tables

## Authentication Architecture

- **Method**: JWT (JSON Web Tokens) via Flask-JWT-Extended
- **Token lifetime**: 1 hour (configurable via `JWT_ACCESS_TOKEN_EXPIRES`)
- **Roles**: `admin`, `manager`, `viewer`
- **Token payload (claims)**: `user_id`, `email`, `role`, `restaurant_id`

### Role Permissions Matrix

| Endpoint Group | admin | manager | viewer |
|---------------|-------|---------|--------|
| Auth (login/register) | Yes | Yes | Yes |
| Dashboard (read) | Yes | Yes | Yes |
| Recommendations (read) | Yes | Yes | Yes |
| Recommendations (act) | Yes | Yes | No |
| Alerts (read) | Yes | Yes | Yes |
| Alerts (acknowledge) | Yes | Yes | No |
| Restaurants (CRUD) | Yes | No | No |
| Shifts (create/update) | Yes | Yes | No |
| Shifts (read) | Yes | Yes | Yes |
| Settings/Config | Yes | Yes | No |

---

## API Endpoint Specifications

### 1. Auth Endpoints — `app/api/auth.py`

Blueprint: `auth_bp = Blueprint('auth', __name__)`

#### POST `/api/auth/register`
**Access**: Public (no auth required)
**Request Body**:
```json
{
    "email": "manager@restaurant.com",
    "password": "securepass123",
    "first_name": "John",
    "last_name": "Smith",
    "role": "manager",
    "restaurant_id": "uuid-of-restaurant"
}
```
**Logic**:
1. Validate all required fields are present
2. Check email is not already registered
3. Validate role is one of: "admin", "manager", "viewer"
4. Validate restaurant_id exists in database
5. Hash password with bcrypt
6. Create User record
7. Return user data (without password_hash)

**Success Response** (201):
```json
{
    "message": "User registered successfully",
    "user": { ...user.to_dict() }
}
```
**Error Responses**: 400 (validation), 409 (email exists)

#### POST `/api/auth/login`
**Access**: Public
**Request Body**:
```json
{
    "email": "manager@restaurant.com",
    "password": "securepass123"
}
```
**Logic**:
1. Find user by email
2. Verify password with bcrypt
3. Check `is_active` is True
4. Generate JWT with additional claims: `role`, `restaurant_id`, `user_id`
5. Return token and user info

**Success Response** (200):
```json
{
    "access_token": "eyJ...",
    "user": { ...user.to_dict() }
}
```
**Error Responses**: 401 (invalid credentials), 403 (account deactivated)

**JWT Token Creation**:
```python
from flask_jwt_extended import create_access_token

access_token = create_access_token(
    identity=user.user_id,
    additional_claims={
        'email': user.email,
        'role': user.role,
        'restaurant_id': user.restaurant_id
    }
)
```

#### GET `/api/auth/me`
**Access**: Any authenticated user
**Logic**: Return current user info from JWT
**Success Response** (200): `{ "user": { ...user.to_dict() } }`

---

### 2. Dashboard Endpoints — `app/api/dashboard.py`

Blueprint: `dashboard_bp = Blueprint('dashboard', __name__)`

#### GET `/api/dashboard/current`
**Access**: Authenticated (any role)
**Query Params**: `restaurant_id` (optional — defaults to user's restaurant from JWT)
**Logic**:
1. Get the currently active shift for the restaurant (status="active")
2. Get the most recent OperationalSnapshot for that shift
3. Get active recommendations (is_active=True) for the shift, ordered by priority
4. Get unacknowledged alerts for the shift, ordered by severity
5. Return everything in a single response

**Success Response** (200):
```json
{
    "restaurant": { ...restaurant.to_dict() },
    "current_shift": { ...shift.to_dict() },
    "latest_snapshot": { ...snapshot.to_dict() },
    "active_recommendations": [ ...list of recommendation.to_dict() ],
    "active_alerts": [ ...list of alert.to_dict() ],
    "summary": {
        "total_orders": 45,
        "avg_ticket_time_sec": 142,
        "staff_count": 8,
        "unacknowledged_alerts": 3,
        "pending_recommendations": 5
    }
}
```
**Error**: 404 if no active shift found

#### GET `/api/dashboard/metrics`
**Access**: Authenticated (any role)
**Query Params**:
- `shift_id` (required)
- `minutes` (optional, default=60) — how far back to pull snapshots
**Logic**:
1. Get all OperationalSnapshots for the shift within the time window
2. Compute trends: order volume over time, avg ticket time over time, staff count over time
3. Return as time-series arrays suitable for charting

**Success Response** (200):
```json
{
    "shift_id": "uuid",
    "time_range_minutes": 60,
    "snapshots": [
        {
            "captured_at": "2026-05-10T12:00:00Z",
            "total_orders": 32,
            "avg_ticket_time_sec": 125,
            "staff_count": 7,
            "dine_in_orders": 10,
            "drive_thru_orders": 12,
            "pickup_orders": 5,
            "delivery_orders": 5
        }
    ]
}
```

#### GET `/api/dashboard/trends`
**Access**: Authenticated (any role)
**Query Params**:
- `restaurant_id` (optional)
- `days` (optional, default=7)
**Logic**: Aggregate historical data across recent shifts for the Trends & Analytics view
**Response**: Daily summaries with avg orders, avg ticket time, staff utilization, recommendation acceptance rates

---

### 3. Recommendations Endpoints — `app/api/recommendations.py`

Blueprint: `recommendations_bp = Blueprint('recommendations', __name__)`

#### GET `/api/recommendations/`
**Access**: Authenticated (any role)
**Query Params**:
- `shift_id` (required)
- `active_only` (optional, default=true)
- `rec_type` (optional filter: "labor", "prep", "inventory", "alert")
- `priority` (optional filter: "high", "medium", "low")
**Logic**: Return recommendations matching filters, ordered by priority (high first) then created_at (newest first)
**Response**: `{ "recommendations": [...] }`

#### GET `/api/recommendations/<recommendation_id>`
**Access**: Authenticated (any role)
**Logic**: Return single recommendation with its actions
**Response**: `{ "recommendation": { ...to_dict(), "actions": [...] } }`

#### POST `/api/recommendations/<recommendation_id>/action`
**Access**: Authenticated (manager or admin only — use `@role_required('admin', 'manager')`)
**Request Body**:
```json
{
    "response_type": "accepted",
    "notes": "Moving 2 staff from front to kitchen"
}
```
**Logic**:
1. Validate recommendation exists and is active
2. Validate response_type is one of: "accepted", "deferred", "rejected"
3. Create RecommendationAction record with current user_id
4. If response is "rejected", set recommendation.is_active = False
5. Return the action record

**Success Response** (201): `{ "action": { ...action.to_dict() } }`

---

### 4. Alerts Endpoints — `app/api/alerts.py`

Blueprint: `alerts_bp = Blueprint('alerts', __name__)`

#### GET `/api/alerts/`
**Access**: Authenticated (any role)
**Query Params**:
- `shift_id` (required)
- `acknowledged` (optional: "true"/"false", default shows all)
- `severity` (optional filter: "critical", "warning", "info")
**Logic**: Return alerts matching filters, ordered by severity (critical first) then created_at
**Response**: `{ "alerts": [...] }`

#### PUT `/api/alerts/<alert_id>/acknowledge`
**Access**: Authenticated (manager or admin only)
**Logic**:
1. Find alert by ID
2. Set `is_acknowledged = True`
3. Set `acknowledged_by = current_user_id`
4. Set `acknowledged_at = datetime.utcnow()`
5. Commit and return updated alert

**Success Response** (200): `{ "alert": { ...alert.to_dict() } }`
**Error**: 400 if already acknowledged, 404 if not found

---

### 5. Restaurants Endpoints — `app/api/restaurants.py`

Blueprint: `restaurants_bp = Blueprint('restaurants', __name__)`

#### GET `/api/restaurants/`
**Access**: Admin only
**Logic**: Return all restaurants
**Response**: `{ "restaurants": [...] }`

#### GET `/api/restaurants/<restaurant_id>`
**Access**: Authenticated (any role, but only their own restaurant unless admin)
**Response**: `{ "restaurant": { ...to_dict() } }`

#### POST `/api/restaurants/`
**Access**: Admin only
**Request Body**: All restaurant fields except restaurant_id and created_at
**Response** (201): `{ "restaurant": { ...to_dict() } }`

#### PUT `/api/restaurants/<restaurant_id>`
**Access**: Admin only
**Logic**: Update specified fields
**Response**: `{ "restaurant": { ...to_dict() } }`

---

### 6. Shifts Endpoints — `app/api/shifts.py`

Blueprint: `shifts_bp = Blueprint('shifts', __name__)`

#### GET `/api/shifts/`
**Access**: Authenticated (any role)
**Query Params**:
- `restaurant_id` (optional — defaults to user's restaurant)
- `status` (optional: "active", "completed", "cancelled")
- `date` (optional: YYYY-MM-DD)
**Response**: `{ "shifts": [...] }`

#### GET `/api/shifts/<shift_id>`
**Access**: Authenticated
**Response**: `{ "shift": { ...to_dict() } }` including snapshot count and recommendation count

#### POST `/api/shifts/`
**Access**: Admin or Manager
**Request Body**:
```json
{
    "restaurant_id": "uuid",
    "shift_date": "2026-05-10",
    "start_time": "2026-05-10T06:00:00",
    "end_time": "2026-05-10T14:00:00",
    "shift_type": "morning",
    "manager_id": "uuid (optional)"
}
```
**Response** (201): `{ "shift": { ...to_dict() } }`

#### PUT `/api/shifts/<shift_id>`
**Access**: Admin or Manager
**Logic**: Update status, manager, times
**Response**: `{ "shift": { ...to_dict() } }`

---

## Service Layer Implementation

### `app/services/auth_service.py`

```python
class AuthService:
    @staticmethod
    def register_user(data):
        """Validate input, check duplicates, hash password, create user."""
        pass

    @staticmethod
    def login_user(email, password):
        """Find user, verify password, generate JWT token."""
        pass

    @staticmethod
    def get_current_user(user_id):
        """Get user by ID from JWT identity."""
        pass
```

### `app/services/dashboard_service.py`

```python
class DashboardService:
    @staticmethod
    def get_current_dashboard(restaurant_id):
        """Get active shift, latest snapshot, active recs, active alerts."""
        pass

    @staticmethod
    def get_shift_metrics(shift_id, minutes=60):
        """Get time-series snapshot data for charting."""
        pass

    @staticmethod
    def get_trends(restaurant_id, days=7):
        """Aggregate historical data across recent shifts."""
        pass
```

## Implementation Pattern

For each API endpoint, follow this pattern:

```python
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    # 1. Validate input
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400

    # 2. Call service layer
    result = AuthService.login_user(data['email'], data['password'])

    # 3. Handle errors from service
    if 'error' in result:
        return jsonify(result), result.get('status_code', 401)

    # 4. Return success
    return jsonify(result), 200
```

## Error Response Format

All errors must follow this consistent format:
```json
{
    "error": "Short error type",
    "message": "Human-readable explanation"
}
```

## Verification Checklist

After implementing all endpoints:

1. **Auth flow works end-to-end**:
   ```bash
   # Register
   curl -X POST http://localhost:5000/api/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email":"test@test.com","password":"test123","first_name":"Test","last_name":"User","role":"manager","restaurant_id":"<valid_id>"}'

   # Login
   curl -X POST http://localhost:5000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"test@test.com","password":"test123"}'

   # Access protected route
   curl http://localhost:5000/api/auth/me \
     -H "Authorization: Bearer <token>"
   ```

2. **Role-based access control works**: Viewer cannot POST to `/api/recommendations/<id>/action`

3. **Dashboard endpoint returns complete data structure** when active shift and snapshots exist

4. **All endpoints return proper error codes**: 400, 401, 403, 404 as appropriate

5. **Write at least 3 pytest tests** in `tests/test_auth.py`:
   - Test successful registration
   - Test successful login returns JWT
   - Test accessing protected route without token returns 401

6. **Write at least 2 pytest tests** in `tests/test_dashboard.py`:
   - Test dashboard returns 404 when no active shift
   - Test dashboard returns data when shift exists

## What NOT To Do

- Do NOT implement the recommendation generation logic (that's Session 5)
- Do NOT implement the alert generation logic (that's Session 5)
- Do NOT write seed data (that's Session 4)
- Do NOT build any frontend
- Do NOT use session-based auth — JWT only
- Do NOT store tokens in a database — they are stateless
