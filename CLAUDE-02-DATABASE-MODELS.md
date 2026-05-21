# CLAUDE.md — Session 2: Database Schema & SQLAlchemy Models

## BEFORE YOU START — Context Protocol

1. **Read `CLAUDE.md`** (the master project context file in this directory)
2. **Read `HANDOFF.md`** — Session 1 should have documented exactly what files it created, any naming deviations, and the actual import paths. **Use those actual paths**, not the ones in this instruction file, if they differ.
3. Verify Session 1's work exists: `app/__init__.py`, `app/extensions.py`, `config.py`, `requirements.txt` should all be present.
4. Then proceed with the work below.

## WHEN YOU FINISH — Handoff Protocol

After completing all steps and verification:
1. **Append your handoff section to `HANDOFF.md`** using the template defined in that file
2. Include: every model file created, the exact `__tablename__` values, column names, relationship names, and verification output
3. Document any deviations (e.g., if you had to adjust a type for SQLite compatibility)
4. This is **mandatory** — Sessions 3, 4, and 5 all depend on knowing your exact model structure

---

## Mission

Implement all 7 SQLAlchemy ORM models for the OpSync backend, matching the approved database schema from the Project Design and Solution Architecture document exactly. Create the database migration and verify all tables are created correctly.

## Prerequisites

Session 1 (Project Setup) must be complete. The following must exist:
- `opsync-backend/` project structure
- `app/extensions.py` with `db = SQLAlchemy()`
- `app/__init__.py` with the app factory
- `config.py` with SQLite as the dev database
- `requirements.txt` installed

## Database Engine

- **Development**: SQLite (file-based, `sqlite:///opsync_dev.db`)
- **Production**: PostgreSQL 16
- All models must be compatible with BOTH engines
- Use `sa.Text` instead of `JSONB` with a note that production should use `JSONB`
- UUIDs: Use `String(36)` for SQLite compatibility; store as hex strings via `uuid.uuid4().__str__()`

## Entity-Relationship Summary

```
Restaurant (1) ──── (*) Shift
Restaurant (1) ──── (*) User
Shift (1) ──── (*) OperationalSnapshot
Shift (1) ──── (*) Recommendation
Shift (1) ──── (*) Alert
OperationalSnapshot (1) ──── (*) Recommendation
OperationalSnapshot (1) ──── (*) Alert
Recommendation (1) ──── (*) RecommendationAction
User (1) ──── (*) RecommendationAction
User (1) ──── (*) Alert (acknowledged_by)
User (1) ──── (*) Shift (manager_id)
```

---

## Model Specifications

### Model 1: `app/models/restaurant.py` — Restaurant

| Field | SQLAlchemy Type | Constraints | Description |
|-------|----------------|-------------|-------------|
| restaurant_id | `String(36)` | PK, default=uuid4 | Unique identifier |
| name | `String(100)` | NOT NULL | Restaurant name |
| address | `String(255)` | NOT NULL | Physical street address |
| city | `String(100)` | NOT NULL | City |
| state | `String(2)` | NOT NULL | State abbreviation (e.g., "TX") |
| zip_code | `String(10)` | NOT NULL | Postal code |
| format_type | `String(20)` | NOT NULL | One of: "drive_thru", "dine_in", "combo" |
| open_time | `Time` | NOT NULL | Default daily opening time |
| close_time | `Time` | NOT NULL | Default daily closing time |
| created_at | `DateTime` | NOT NULL, default=utcnow | Record creation timestamp |

**Relationships:**
- `shifts` → one-to-many with Shift (backref: `restaurant`)
- `users` → one-to-many with User (backref: `restaurant`)

**Methods to include:**
- `to_dict()` → returns all fields as a serializable dictionary
- `__repr__()` → `<Restaurant {name} ({restaurant_id})>`

---

### Model 2: `app/models/user.py` — User

| Field | SQLAlchemy Type | Constraints | Description |
|-------|----------------|-------------|-------------|
| user_id | `String(36)` | PK, default=uuid4 | Unique identifier |
| restaurant_id | `String(36)` | FK → restaurant.restaurant_id, NOT NULL | Associated restaurant |
| email | `String(150)` | NOT NULL, UNIQUE | Login credential |
| password_hash | `String(255)` | NOT NULL | Bcrypt-hashed password |
| first_name | `String(50)` | NOT NULL | First name |
| last_name | `String(50)` | NOT NULL | Last name |
| role | `String(20)` | NOT NULL | One of: "admin", "manager", "viewer" |
| is_active | `Boolean` | NOT NULL, default=True | Account active status |
| created_at | `DateTime` | NOT NULL, default=utcnow | Record creation timestamp |

**Relationships:**
- `recommendation_actions` → one-to-many with RecommendationAction (backref: `user`)
- `managed_shifts` → one-to-many with Shift (backref: `manager`, foreign_keys=[Shift.manager_id])
- `acknowledged_alerts` → one-to-many with Alert (backref: `acknowledger`, foreign_keys=[Alert.acknowledged_by])

**Methods to include:**
- `set_password(password)` → hash with bcrypt and store in `password_hash`
- `check_password(password)` → verify against `password_hash`
- `to_dict()` → returns all fields EXCEPT `password_hash`
- `__repr__()` → `<User {email} ({role})>`

> **IMPORTANT**: Import and use `bcrypt` from `app.extensions` for password hashing.

---

### Model 3: `app/models/shift.py` — Shift

| Field | SQLAlchemy Type | Constraints | Description |
|-------|----------------|-------------|-------------|
| shift_id | `String(36)` | PK, default=uuid4 | Unique identifier |
| restaurant_id | `String(36)` | FK → restaurant.restaurant_id, NOT NULL | Associated restaurant |
| manager_id | `String(36)` | FK → users.user_id, NULLABLE | Assigned shift manager |
| shift_date | `Date` | NOT NULL | Date of the shift |
| start_time | `DateTime` | NOT NULL | Shift start timestamp |
| end_time | `DateTime` | NOT NULL | Shift end timestamp |
| shift_type | `String(20)` | NOT NULL | One of: "morning", "lunch", "dinner", "late" |
| status | `String(20)` | NOT NULL, default="active" | One of: "active", "completed", "cancelled" |

**Relationships:**
- `snapshots` → one-to-many with OperationalSnapshot (backref: `shift`)
- `recommendations` → one-to-many with Recommendation (backref: `shift`)
- `alerts` → one-to-many with Alert (backref: `shift`)

**Methods:**
- `to_dict()` → serializable dictionary including manager name if set
- `__repr__()` → `<Shift {shift_type} on {shift_date}>`

---

### Model 4: `app/models/operational_snapshot.py` — OperationalSnapshot

| Field | SQLAlchemy Type | Constraints | Description |
|-------|----------------|-------------|-------------|
| snapshot_id | `String(36)` | PK, default=uuid4 | Unique identifier |
| shift_id | `String(36)` | FK → shift.shift_id, NOT NULL | Associated shift |
| captured_at | `DateTime` | NOT NULL | Timestamp of capture |
| total_orders | `Integer` | NOT NULL | Total active orders across all channels |
| dine_in_orders | `Integer` | NULLABLE | Current dine-in count |
| drive_thru_orders | `Integer` | NULLABLE | Current drive-thru count |
| pickup_orders | `Integer` | NULLABLE | Current pickup count |
| delivery_orders | `Integer` | NULLABLE | Current delivery count |
| avg_ticket_time_sec | `Integer` | NULLABLE | Average ticket time in seconds |
| staff_count | `Integer` | NOT NULL | Total staff on shift |
| kitchen_staff | `Integer` | NULLABLE | Kitchen station staff |
| front_staff | `Integer` | NULLABLE | Front-of-house staff |
| inventory_json | `Text` | NULLABLE | JSON string of inventory levels (use JSONB in PostgreSQL) |

**Relationships:**
- `recommendations` → one-to-many with Recommendation (backref: `snapshot`)
- `alerts` → one-to-many with Alert (backref: `snapshot`)

**Methods:**
- `to_dict()` → serializable dictionary; parse `inventory_json` into a dict if present
- `__repr__()` → `<Snapshot {snapshot_id} at {captured_at}>`

> **NOTE on inventory_json**: Store as a JSON string in SQLite. Use `json.dumps()` when writing and `json.loads()` when reading. Add a `@property` called `inventory` that handles this automatically.

---

### Model 5: `app/models/recommendation.py` — Recommendation

| Field | SQLAlchemy Type | Constraints | Description |
|-------|----------------|-------------|-------------|
| recommendation_id | `String(36)` | PK, default=uuid4 | Unique identifier |
| shift_id | `String(36)` | FK → shift.shift_id, NOT NULL | Associated shift |
| snapshot_id | `String(36)` | FK → operational_snapshot.snapshot_id, NOT NULL | Triggering snapshot |
| rec_type | `String(30)` | NOT NULL | One of: "labor", "prep", "inventory", "alert" |
| priority | `String(10)` | NOT NULL | One of: "high", "medium", "low" |
| title | `String(200)` | NOT NULL | Short title |
| description | `Text` | NOT NULL | Detailed text |
| rationale | `Text` | NOT NULL | Why this was generated |
| suggested_action | `Text` | NOT NULL | What the manager should do |
| created_at | `DateTime` | NOT NULL, default=utcnow | Generation timestamp |
| is_active | `Boolean` | NOT NULL, default=True | Whether still relevant |

**Relationships:**
- `actions` → one-to-many with RecommendationAction (backref: `recommendation`)

**Methods:**
- `to_dict()` → serializable dictionary
- `__repr__()` → `<Recommendation {rec_type}: {title}>`

---

### Model 6: `app/models/recommendation_action.py` — RecommendationAction

| Field | SQLAlchemy Type | Constraints | Description |
|-------|----------------|-------------|-------------|
| action_id | `String(36)` | PK, default=uuid4 | Unique identifier |
| recommendation_id | `String(36)` | FK → recommendation.recommendation_id, NOT NULL | Associated recommendation |
| user_id | `String(36)` | FK → users.user_id, NOT NULL | Responding manager |
| response_type | `String(20)` | NOT NULL | One of: "accepted", "deferred", "rejected" |
| notes | `Text` | NULLABLE | Optional manager notes |
| responded_at | `DateTime` | NOT NULL, default=utcnow | Response timestamp |

**Methods:**
- `to_dict()` → serializable dictionary including user name
- `__repr__()` → `<Action {response_type} by {user_id}>`

---

### Model 7: `app/models/alert.py` — Alert

| Field | SQLAlchemy Type | Constraints | Description |
|-------|----------------|-------------|-------------|
| alert_id | `String(36)` | PK, default=uuid4 | Unique identifier |
| shift_id | `String(36)` | FK → shift.shift_id, NOT NULL | Associated shift |
| snapshot_id | `String(36)` | FK → operational_snapshot.snapshot_id, NOT NULL | Triggering snapshot |
| alert_type | `String(30)` | NOT NULL | One of: "queue_surge", "stockout_risk", "labor_imbalance" |
| severity | `String(10)` | NOT NULL | One of: "critical", "warning", "info" |
| message | `Text` | NOT NULL | Alert message for manager |
| is_acknowledged | `Boolean` | NOT NULL, default=False | Manager acknowledged |
| acknowledged_by | `String(36)` | FK → users.user_id, NULLABLE | Who acknowledged |
| created_at | `DateTime` | NOT NULL, default=utcnow | Trigger timestamp |
| acknowledged_at | `DateTime` | NULLABLE | Acknowledgment timestamp |

**Methods:**
- `to_dict()` → serializable dictionary
- `__repr__()` → `<Alert {alert_type} ({severity})>`

---

## `app/models/__init__.py`

Import all models so they are registered with SQLAlchemy:

```python
from app.models.restaurant import Restaurant
from app.models.user import User
from app.models.shift import Shift
from app.models.operational_snapshot import OperationalSnapshot
from app.models.recommendation import Recommendation
from app.models.recommendation_action import RecommendationAction
from app.models.alert import Alert

__all__ = [
    'Restaurant', 'User', 'Shift', 'OperationalSnapshot',
    'Recommendation', 'RecommendationAction', 'Alert',
]
```

## Implementation Notes

1. **UUID generation**: Use this pattern for all primary keys:
   ```python
   import uuid
   
   def generate_uuid():
       return str(uuid.uuid4())
   
   # In column definition:
   restaurant_id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
   ```

2. **Table names**: Use the `__tablename__` attribute explicitly:
   - `restaurant`, `users`, `shift`, `operational_snapshot`, `recommendation`, `recommendation_action`, `alert`
   - NOTE: The users table is `users` (plural) because `user` is a reserved word in some databases

3. **Foreign key naming**: Use the full `tablename.column_name` format:
   ```python
   restaurant_id = db.Column(db.String(36), db.ForeignKey('restaurant.restaurant_id'), nullable=False)
   ```

4. **DateTime defaults**: Use `datetime.utcnow` (without parentheses) as the default:
   ```python
   from datetime import datetime
   created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
   ```

## Verification Checklist

After implementing all models:

1. Run the app and verify the database is created:
   ```bash
   python -c "
   from app import create_app
   from app.extensions import db
   app = create_app('development')
   with app.app_context():
       db.create_all()
       print('All tables created successfully')
       # List all tables
       from sqlalchemy import inspect
       inspector = inspect(db.engine)
       tables = inspector.get_table_names()
       print(f'Tables: {tables}')
       assert len(tables) == 7, f'Expected 7 tables, got {len(tables)}'
   "
   ```

2. Verify all relationships work:
   ```bash
   python -c "
   from app import create_app
   from app.extensions import db
   from app.models import Restaurant, User
   app = create_app('testing')
   with app.app_context():
       db.create_all()
       r = Restaurant(name='Test', address='123 Main', city='Dallas', state='TX', zip_code='75001', format_type='combo', open_time='06:00', close_time='22:00')
       db.session.add(r)
       db.session.commit()
       u = User(restaurant_id=r.restaurant_id, email='test@test.com', password_hash='temp', first_name='Test', last_name='User', role='manager')
       db.session.add(u)
       db.session.commit()
       assert r.users[0].email == 'test@test.com'
       print('Relationships verified')
   "
   ```

3. Verify `to_dict()` works on each model and returns JSON-serializable data

4. Verify User password hashing:
   ```bash
   python -c "
   from app import create_app
   from app.models import User
   app = create_app('testing')
   with app.app_context():
       u = User(restaurant_id='fake', email='a@b.com', first_name='A', last_name='B', role='admin')
       u.set_password('test123')
       assert u.check_password('test123')
       assert not u.check_password('wrong')
       print('Password hashing verified')
   "
   ```

## What NOT To Do

- Do NOT use `Integer` auto-increment for primary keys — use UUID strings
- Do NOT use PostgreSQL-specific types (JSONB, UUID) — use SQLite-compatible types
- Do NOT implement any API routes (that's Session 3)
- Do NOT implement service layer logic
- Do NOT write seed data (that's Session 4)
- Do NOT skip `to_dict()` methods — the API layer depends on them
