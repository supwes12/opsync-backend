# CLAUDE.md — Session 4: Seed Data Scripts

## BEFORE YOU START — Context Protocol

1. **Read `CLAUDE.md`** (the master project context file in this directory)
2. **Read `HANDOFF.md`** — Sessions 1, 2, and 3 should all have handoff entries. Pay special attention to:
   - **Session 2's handoff**: The exact model field names, relationship names, and `set_password()` method signature. Use these when creating seed records.
   - **Session 3's handoff**: The Flask CLI command registration (if it was added to `app/__init__.py`), and the API endpoints so you can verify seed data works with them.
3. **Before writing any seed code**, verify the models by reading the actual model files on disk:
   ```bash
   cat app/models/user.py  # Check exact field names
   cat app/models/restaurant.py  # Check exact field names
   ```
4. If any field names, table names, or relationship names differ from what this instruction file says, **use what's actually in the code**.
5. Then proceed with the work below.

## WHEN YOU FINISH — Handoff Protocol

After completing all steps and verification:
1. **Append your handoff section to `HANDOFF.md`** using the template defined in that file
2. Include: exact record counts per table, the test credentials (email/password combos), which shift is marked "active", and the snapshot time range
3. Document the restaurant_ids, user_ids, and shift_ids that were created (Session 5 needs these to run algorithm evaluation)
4. This is **mandatory** — Session 5's algorithms need to query this data

---

## Mission

Create comprehensive seed data scripts that populate every database table with realistic, interconnected restaurant operational data suitable for development testing and demo purposes. The data must tell a coherent story across a full day of restaurant operations.

## Prerequisites

Sessions 1–3 must be complete:
- All 7 SQLAlchemy models are implemented and functional
- Database creates all tables successfully
- User model has working `set_password()` method
- App factory and extensions work

## Seed Script Location

`app/seed/seed_data.py`

Also create a CLI command so it can be run as:
```bash
python -m app.seed.seed_data
# OR
flask seed
```

## Data Generation Requirements

### 1. Restaurants (3 records)

Create 3 restaurants representing different formats from the design doc:

| Name | Format | City | State | Hours |
|------|--------|------|-------|-------|
| OpSync Burger - Downtown | drive_thru | Dallas | TX | 6:00 AM – 11:00 PM |
| OpSync Burger - Suburban | combo | Plano | TX | 7:00 AM – 10:00 PM |
| OpSync Burger - Airport | dine_in | Irving | TX | 5:00 AM – 12:00 AM |

Use realistic addresses (make them up but plausible for the city).

### 2. Users (9 records — 3 per restaurant)

For each restaurant, create:

| Email Pattern | Role | Password (all the same for dev) |
|--------------|------|--------------------------------|
| `admin@{city}.opsync.com` | admin | `admin123` |
| `manager@{city}.opsync.com` | manager | `manager123` |
| `viewer@{city}.opsync.com` | viewer | `viewer123` |

Give each user a realistic first/last name. Use the User model's `set_password()` method for hashing.

### 3. Shifts (9 records — 3 per restaurant)

For the primary restaurant (Downtown), create a full day of shifts for **today's date**:

| Shift Type | Start | End | Status | Manager |
|-----------|-------|-----|--------|---------|
| morning | 6:00 AM | 12:00 PM | completed | manager user |
| lunch | 11:00 AM | 5:00 PM | active | manager user |
| dinner | 4:00 PM | 11:00 PM | active | manager user |

For the other two restaurants, create at least one active shift each.

> **IMPORTANT**: Use `datetime.today()` for shift dates so the data is always "current" when seeded.

### 4. Operational Snapshots (60+ records)

For the **Downtown lunch shift**, generate a time series of snapshots every 5 minutes spanning 2 hours (24 snapshots minimum). The data should tell a realistic story:

**Ramp-up phase (11:00 AM – 12:00 PM)**:
- Orders gradually increase from 5 → 35 total
- Drive-thru dominates (40% of orders), dine-in (25%), pickup (20%), delivery (15%)
- Ticket time starts at 90s, creeps up to 140s
- Staff count: 6 (kitchen: 3, front: 3)

**Peak phase (12:00 PM – 1:00 PM)**:
- Orders spike to 45–55
- Ticket time rises to 180–240s (triggers alerts)
- Staff stays at 6 but is understaffed
- Inventory levels start dropping (chicken down to 15%, fries down to 25%)

**Cool-down phase (1:00 PM – 2:00 PM)**:
- Orders decline to 20–25
- Ticket time drops back to 100–120s
- Some staff moved or break rotation begins

**inventory_json format**:
```json
{
    "chicken_breast": {"current": 45, "par": 100, "unit": "pieces"},
    "french_fries": {"current": 30, "par": 80, "unit": "lbs"},
    "burger_patties": {"current": 60, "par": 120, "unit": "pieces"},
    "lettuce": {"current": 15, "par": 30, "unit": "heads"},
    "tomatoes": {"current": 20, "par": 40, "unit": "lbs"},
    "soda_syrup": {"current": 3, "par": 6, "unit": "boxes"},
    "cups_large": {"current": 200, "par": 500, "unit": "count"},
    "napkins": {"current": 400, "par": 1000, "unit": "count"}
}
```

Adjust quantities realistically across snapshots (items decrease during peak, some get restocked).

Also create at least 10 snapshots for the morning shift (completed) to support the trends view.

### 5. Recommendations (8–12 records)

Generate recommendations that would realistically be triggered by the snapshot data. Link each to the appropriate shift and triggering snapshot.

**Examples to create**:

| Type | Priority | Title | Triggered During |
|------|----------|-------|-----------------|
| labor | high | "Move 1 staff from front to kitchen" | Peak phase (ticket time > 180s) |
| labor | medium | "Consider calling in additional staff" | Peak phase (orders > 50, staff = 6) |
| inventory | high | "Chicken breast approaching stockout" | When chicken < 20% par |
| inventory | medium | "French fries below threshold" | When fries < 30% par |
| prep | medium | "Start prepping dinner rush items" | 1:00 PM (before dinner shift) |
| labor | low | "Front counter staff can take break" | Cool-down phase |
| alert | high | "Drive-thru queue exceeding 5 minutes" | Peak when ticket > 240s |
| prep | low | "Restock cup station" | When cups < 50% par |

Set `is_active = True` for 5 of them, `is_active = False` for the rest (already addressed).

### 6. Recommendation Actions (5–6 records)

Create manager responses for some of the recommendations:

| Recommendation | Response | Notes |
|---------------|----------|-------|
| "Move 1 staff" | accepted | "Moved Sarah to grill station" |
| "Call in staff" | deferred | "Monitoring for 15 more minutes" |
| "Chicken stockout" | accepted | "Placed emergency order" |
| "Drive-thru queue" | accepted | "Opened second drive-thru window" |
| "Restock cups" | rejected | "Already handled by morning crew" |

Link each to the manager user and appropriate recommendation.

### 7. Alerts (6–8 records)

Generate alerts triggered by threshold violations in the snapshot data:

| Type | Severity | Message | Acknowledged? |
|------|----------|---------|--------------|
| queue_surge | critical | "Drive-thru avg wait time exceeds 5 minutes" | Yes |
| queue_surge | warning | "Total order queue 50% above 30-min average" | Yes |
| labor_imbalance | critical | "Kitchen understaffed: 3 staff handling 50+ orders/hr" | No |
| stockout_risk | warning | "Chicken breast at 15% of daily par level" | No |
| stockout_risk | info | "French fries at 25% of daily par level" | Yes |
| labor_imbalance | warning | "Front counter overstaffed relative to current demand" | No |

For acknowledged alerts, set `acknowledged_by` to the manager user and `acknowledged_at` to a realistic timestamp.

---

## Implementation Structure

```python
# app/seed/seed_data.py

import json
from datetime import datetime, date, time, timedelta
from app import create_app
from app.extensions import db
from app.models import (
    Restaurant, User, Shift, OperationalSnapshot,
    Recommendation, RecommendationAction, Alert
)

def clear_all_data():
    """Drop all data in reverse dependency order."""
    RecommendationAction.query.delete()
    Alert.query.delete()
    Recommendation.query.delete()
    OperationalSnapshot.query.delete()
    Shift.query.delete()
    User.query.delete()
    Restaurant.query.delete()
    db.session.commit()
    print("Cleared all existing data.")

def seed_restaurants():
    """Create 3 restaurant locations."""
    # ... return list of created restaurants
    pass

def seed_users(restaurants):
    """Create 3 users per restaurant (admin, manager, viewer)."""
    # ... return dict mapping restaurant_id to user list
    pass

def seed_shifts(restaurants, users):
    """Create shifts for today."""
    # ... return list of created shifts
    pass

def generate_snapshot_series(shift, phase, count):
    """Generate realistic time-series snapshots for a shift phase."""
    # Use random variation (+/- 10-15%) around base values
    # Each snapshot should be slightly different from the last
    pass

def seed_snapshots(shifts):
    """Create operational snapshots with realistic time-series data."""
    # ... return list of created snapshots
    pass

def seed_recommendations(shifts, snapshots):
    """Create recommendations linked to appropriate shifts and snapshots."""
    # ... return list of created recommendations
    pass

def seed_recommendation_actions(recommendations, users):
    """Create manager responses to recommendations."""
    pass

def seed_alerts(shifts, snapshots, users):
    """Create threshold-triggered alerts."""
    pass

def seed_all():
    """Run the complete seed pipeline."""
    print("Starting database seed...")
    clear_all_data()

    restaurants = seed_restaurants()
    print(f"  Created {len(restaurants)} restaurants")

    users = seed_users(restaurants)
    print(f"  Created {sum(len(v) for v in users.values())} users")

    shifts = seed_shifts(restaurants, users)
    print(f"  Created {len(shifts)} shifts")

    snapshots = seed_snapshots(shifts)
    print(f"  Created {len(snapshots)} operational snapshots")

    recommendations = seed_recommendations(shifts, snapshots)
    print(f"  Created {len(recommendations)} recommendations")

    seed_recommendation_actions(recommendations, users)
    print(f"  Created recommendation actions")

    seed_alerts(shifts, snapshots, users)
    print(f"  Created alerts")

    print("Database seed complete!")

if __name__ == '__main__':
    app = create_app('development')
    with app.app_context():
        db.create_all()
        seed_all()
```

### Flask CLI Command

Add to `app/__init__.py` inside `create_app()`:

```python
@app.cli.command('seed')
def seed_command():
    """Seed the database with sample data."""
    from app.seed.seed_data import seed_all
    seed_all()
```

## Data Realism Guidelines

- Use `random.uniform()` and `random.randint()` for natural variation
- Snapshot values should trend logically (orders don't jump from 5 to 50 in one interval)
- Inventory should only decrease over time (or jump up when "restocked")
- Ticket times correlate with order volume (more orders = higher ticket time)
- Staff count should remain stable within a phase unless a recommendation was "accepted"
- Use `import random; random.seed(42)` for reproducible results across runs

## Verification Checklist

After running the seed script:

1. Run the seed: `python -m app.seed.seed_data` — should print counts for all tables
2. Verify record counts:
   ```python
   python -c "
   from app import create_app
   from app.extensions import db
   from app.models import *
   app = create_app('development')
   with app.app_context():
       print(f'Restaurants: {Restaurant.query.count()}')   # 3
       print(f'Users: {User.query.count()}')               # 9
       print(f'Shifts: {Shift.query.count()}')              # 9+
       print(f'Snapshots: {OperationalSnapshot.query.count()}')  # 60+
       print(f'Recommendations: {Recommendation.query.count()}')  # 8-12
       print(f'Actions: {RecommendationAction.query.count()}')    # 5-6
       print(f'Alerts: {Alert.query.count()}')              # 6-8
   "
   ```
3. Verify a user can log in with seeded credentials
4. Verify the dashboard endpoint returns populated data for the active shift
5. Verify `inventory_json` parses correctly from snapshots
6. Run seed twice — it should clear and re-seed cleanly (idempotent)

## What NOT To Do

- Do NOT generate random UUIDs for foreign keys — always reference actual created records
- Do NOT use hardcoded dates — use `date.today()` and `datetime.now()` so data stays fresh
- Do NOT create orphaned records — every FK must point to a real parent
- Do NOT skip the clear step — seed must be idempotent
- Do NOT generate flat/boring data — snapshots should tell the story of a real lunch rush
