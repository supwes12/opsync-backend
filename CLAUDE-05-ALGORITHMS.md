# CLAUDE.md — Session 5: Algorithms & Recommendation Engine

## BEFORE YOU START — Context Protocol

1. **Read `CLAUDE.md`** (the master project context file in this directory)
2. **Read `HANDOFF.md`** — All 4 prior sessions should have handoff entries. Pay special attention to:
   - **Session 2's handoff**: Exact model field names, especially `OperationalSnapshot` fields (the algorithm queries these directly)
   - **Session 3's handoff**: The dashboard blueprint and how the `/api/dashboard/evaluate` endpoint should be wired up
   - **Session 4's handoff**: The actual shift_ids and snapshot data that's in the database — you need these to test the algorithms
3. **Before writing any algorithm code**, verify the database has data:
   ```bash
   python -c "
   from app import create_app; from app.models import *
   app = create_app('development')
   with app.app_context():
       print(f'Snapshots: {OperationalSnapshot.query.count()}')
       print(f'Active shifts: {Shift.query.filter_by(status=\"active\").count()}')
   "
   ```
   If counts are 0, run the seed script first: `python -m app.seed.seed_data`
4. **Read the actual model files** to confirm field names before querying them:
   ```bash
   cat app/models/operational_snapshot.py
   cat app/models/recommendation.py
   cat app/models/alert.py
   ```
5. Then proceed with the work below.

## WHEN YOU FINISH — Handoff Protocol

After completing all steps and verification:
1. **Append your handoff section to `HANDOFF.md`** using the template defined in that file
2. Include: which services were implemented, verification output showing recommendations/alerts generated, and the trigger endpoint details
3. This is the final session — your handoff marks the project as build-complete

---

## Mission

Implement the three core algorithmic services that power OpSync's intelligence layer: demand forecasting, labor optimization recommendations, and threshold-based alert generation. These services analyze operational snapshots and generate actionable recommendations and alerts for restaurant managers.

## Prerequisites

Sessions 1–4 must be complete:
- All models implemented and working
- Database seeded with realistic snapshot data
- API endpoints exist (recommendations and alerts endpoints ready to serve generated data)
- Service layer stubs exist in `app/services/`

## Architecture Overview

```
OperationalSnapshot (input)
        │
        ├──→ ForecastService     → Demand predictions (stored as metadata)
        │         │
        ├──→ RecommendationEngine → Recommendation records (written to DB)
        │         │
        └──→ AlertService        → Alert records (written to DB)
                  │
          Dashboard API (output) → Manager sees recommendations + alerts
```

All three services are designed to run on each new OperationalSnapshot. In production, Celery workers would trigger them. For the MVP, they can also be called synchronously from a manual trigger endpoint.

---

## Service 1: `app/services/forecast_service.py` — Short-Horizon Demand Forecasting

### Purpose
Predict order volume by channel for the next 15–60 minutes based on historical snapshot patterns.

### Algorithm (Simplified for MVP)

Since the MVP runs on SQLite with limited historical data, use a **weighted moving average** approach rather than full ARIMA/XGBoost. This is a valid simplification for the pilot — the design doc specifies these as the production algorithms, but the MVP proves the workflow.

```python
class ForecastService:
    """
    Short-horizon demand forecasting using weighted moving average.
    
    Production upgrade path: Replace with ARIMA + XGBoost ensemble
    as described in the Design Document Algorithm 1.
    """
    
    # Weights for recent snapshots (most recent gets highest weight)
    WEIGHTS = [0.35, 0.25, 0.20, 0.12, 0.08]  # Last 5 snapshots
    
    @staticmethod
    def forecast_demand(shift_id, horizon_minutes=30):
        """
        Predict order volume for the next `horizon_minutes`.
        
        Args:
            shift_id: Current shift ID
            horizon_minutes: How far ahead to predict (15, 30, or 60)
        
        Returns:
            dict with predicted values:
            {
                "predicted_total_orders": 48,
                "predicted_by_channel": {
                    "dine_in": 12,
                    "drive_thru": 19,
                    "pickup": 10,
                    "delivery": 7
                },
                "predicted_avg_ticket_time": 165,
                "confidence": "medium",  # low/medium/high based on data availability
                "horizon_minutes": 30,
                "generated_at": "2026-05-10T12:30:00Z"
            }
        
        Algorithm:
        1. Get the last 5 OperationalSnapshots for this shift
        2. If fewer than 3 snapshots, return low-confidence estimate based on averages
        3. Calculate weighted moving average for each metric
        4. Apply a trend multiplier: if orders are increasing, scale up prediction
        5. Apply time-of-day adjustment using historical shift data (if available)
        """
        pass
    
    @staticmethod
    def _calculate_trend(values):
        """
        Calculate trend direction and magnitude from a list of values.
        
        Returns a multiplier:
        - > 1.0 means increasing trend
        - < 1.0 means decreasing trend
        - 1.0 means flat
        
        Use simple linear regression slope:
        slope = (n * sum(x*y) - sum(x)*sum(y)) / (n * sum(x^2) - sum(x)^2)
        Normalize to a multiplier between 0.8 and 1.3
        """
        pass
    
    @staticmethod
    def _get_historical_baseline(restaurant_id, shift_type, hour):
        """
        Get average metrics for this restaurant at this time of day
        from completed shifts. Used as a fallback when current shift
        has limited data.
        """
        pass
```

### Confidence Levels
- **High**: 5+ snapshots available, stable trend, historical data matches
- **Medium**: 3-4 snapshots, some trend detected
- **Low**: Fewer than 3 snapshots or wild fluctuations

---

## Service 2: `app/services/recommendation_engine.py` — Labor Optimization & Recommendations

### Purpose
Compare predicted demand against current staffing and inventory to generate prioritized operational recommendations.

### Algorithm

```python
class RecommendationEngine:
    """
    Generates operational recommendations by comparing current state
    against optimal state derived from demand forecasts.
    
    Implements Algorithm 2 (Labor Optimization) from the Design Document.
    """
    
    # Configurable staffing ratios (orders per staff member per hour)
    KITCHEN_RATIO = 8    # 1 kitchen staff per 8 orders/hour
    FRONT_RATIO = 12     # 1 front staff per 12 orders/hour
    
    # Minimum staff per station (safety threshold — never recommend below this)
    MIN_KITCHEN_STAFF = 2
    MIN_FRONT_STAFF = 1
    
    # Inventory alert thresholds (percentage of par level)
    INVENTORY_CRITICAL = 0.15   # 15% of par → high priority
    INVENTORY_WARNING = 0.30    # 30% of par → medium priority
    
    # Maximum concurrent active recommendations per shift
    MAX_ACTIVE_RECS = 5
    
    @staticmethod
    def evaluate(shift_id, snapshot_id):
        """
        Main entry point. Evaluate the latest snapshot and generate
        recommendations if warranted.
        
        Args:
            shift_id: Current shift
            snapshot_id: The snapshot that triggered this evaluation
        
        Returns:
            list of Recommendation objects created (may be empty)
        
        Steps:
        1. Load the snapshot and current shift state
        2. Get demand forecast from ForecastService
        3. Check labor optimization
        4. Check inventory levels
        5. Check prep timing
        6. Deduplicate against existing active recommendations
        7. Write new recommendations to DB
        """
        pass
    
    @staticmethod
    def _check_labor(snapshot, forecast):
        """
        Compare current staffing against optimal staffing based on demand.
        
        Logic:
        1. Calculate optimal kitchen staff = ceil(predicted_orders_per_hour / KITCHEN_RATIO)
        2. Calculate optimal front staff = ceil(predicted_orders_per_hour / FRONT_RATIO)
        3. Compare against actual staff counts from snapshot
        4. Generate recommendations if gap >= 1 staff member
        
        Priority scoring (from Design Doc):
        - Staffing gap magnitude: 40% weight
        - Predicted demand duration: 30% weight
        - Impact on ticket time: 30% weight
        
        Returns:
            list of recommendation dicts with keys:
            rec_type, priority, title, description, rationale, suggested_action
        """
        pass
    
    @staticmethod
    def _check_inventory(snapshot):
        """
        Check inventory levels against par thresholds.
        
        Logic:
        1. Parse inventory_json from snapshot
        2. For each tracked item, calculate current_pct = current / par
        3. If current_pct < INVENTORY_CRITICAL → high priority rec
        4. If current_pct < INVENTORY_WARNING → medium priority rec
        
        Returns:
            list of recommendation dicts
        """
        pass
    
    @staticmethod
    def _check_prep_timing(snapshot, shift):
        """
        Check if it's time to start prepping for the next shift.
        
        Logic:
        1. If current time is within 60 minutes of shift end
        2. AND there's a subsequent shift scheduled
        3. Generate a prep recommendation
        
        Returns:
            list of recommendation dicts (0 or 1 items)
        """
        pass
    
    @staticmethod
    def _calculate_priority(gap_magnitude, demand_duration_min, ticket_time_impact):
        """
        Calculate priority using the weighted scoring formula from the Design Doc.
        
        Score = (gap_magnitude * 0.4) + (demand_duration * 0.3) + (ticket_impact * 0.3)
        
        Normalize each input to 0-100 scale, then:
        - Score >= 70: "high"
        - Score >= 40: "medium"  
        - Score < 40: "low"
        """
        pass
    
    @staticmethod
    def _deduplicate(new_recs, shift_id):
        """
        Check against existing active recommendations for this shift.
        Don't create a duplicate if a recommendation of the same type
        and similar title already exists and is still active.
        
        Returns: filtered list of truly new recommendations
        """
        pass
```

### Recommendation Templates

Use these templates for generating clear, actionable recommendations:

**Labor — Understaffed Kitchen**:
- Title: "Move {n} staff from front to kitchen"
- Description: "Kitchen is handling {orders} orders with only {current} staff. Optimal staffing for current demand is {optimal}."
- Rationale: "Average ticket time has increased to {ticket_time}s, which exceeds the {threshold}s target. Demand forecast predicts {forecast} orders in the next 30 minutes."
- Suggested Action: "Reassign {n} front-of-house staff to kitchen stations. Priority: grill station first, then prep."

**Labor — Overstaffed Front**:
- Title: "Rotate {n} front counter staff to break"
- Description: "Front counter has {current} staff but current dine-in volume only requires {optimal}."
- Rationale: "Order volume has decreased to {orders} total. {n} front staff can take scheduled breaks without impacting service."
- Suggested Action: "Send {names} on break rotation. Maintain {min} at counter minimum."

**Inventory — Critical**:
- Title: "{item} approaching stockout"
- Description: "{item} is at {pct}% of daily par level ({current} {unit} remaining of {par} {unit} par)."
- Rationale: "At current consumption rate, {item} will run out in approximately {minutes} minutes."
- Suggested Action: "Place emergency restock order or begin substitution protocol for affected menu items."

**Inventory — Warning**:
- Title: "{item} below reorder threshold"
- Description: "{item} is at {pct}% of daily par level."
- Rationale: "Current usage pattern suggests this item may reach critical levels before shift end."
- Suggested Action: "Monitor closely and consider preemptive restock if consumption rate increases."

**Prep — Next Shift**:
- Title: "Start prepping for {next_shift_type} shift"
- Description: "Current shift ends in {minutes} minutes. {next_shift_type} shift starts at {start_time}."
- Rationale: "Prep items for the upcoming shift should be started now to ensure readiness."
- Suggested Action: "Begin prep checklist for {next_shift_type}: {items}."

---

## Service 3: `app/services/alert_service.py` — Threshold-Based Alert Generation

### Purpose
Detect operational anomalies and trigger alerts when metrics exceed configurable thresholds.

### Algorithm

```python
class AlertService:
    """
    Evaluates operational snapshots against configurable thresholds
    and generates alerts. Implements Algorithm 3 from the Design Document.
    
    Alert State Machine:
    1. Threshold crossed once → "triggered" (internal state, not shown)
    2. Threshold crossed for 2 consecutive snapshots → "active" (shown on dashboard)
    3. Condition normal for 3 consecutive snapshots → auto-resolved
    
    Max concurrent active alerts per shift: 5 (prioritized by severity)
    """
    
    # Default thresholds (should be configurable in production)
    THRESHOLDS = {
        'ticket_time_warning': 180,      # seconds
        'ticket_time_critical': 300,     # seconds
        'queue_surge_pct': 1.50,         # 150% of 30-min trailing average
        'inventory_critical_pct': 0.20,  # 20% of par level
        'staff_order_ratio_min': {       # minimum orders-per-staff before alert
            'kitchen': 10,               # if orders/kitchen_staff > 10, understaffed
            'front': 15,
        },
    }
    
    MAX_ACTIVE_ALERTS = 5
    
    @staticmethod
    def evaluate(shift_id, snapshot_id):
        """
        Main entry point. Evaluate latest snapshot against all thresholds.
        
        Args:
            shift_id: Current shift
            snapshot_id: Triggering snapshot
        
        Returns:
            list of Alert objects created
        
        Steps:
        1. Load snapshot
        2. Run each threshold check
        3. Apply state machine logic (check if condition persists)
        4. Auto-resolve alerts where condition returned to normal
        5. Enforce MAX_ACTIVE_ALERTS limit
        6. Write new alerts to DB
        """
        pass
    
    @staticmethod
    def _check_ticket_time(snapshot):
        """
        Check avg_ticket_time_sec against warning (180s) and critical (300s).
        
        Returns:
            list of alert dicts: [{alert_type, severity, message}]
        """
        pass
    
    @staticmethod
    def _check_queue_surge(snapshot, shift_id):
        """
        Check if total_orders exceeds 150% of the trailing 30-minute average.
        
        Logic:
        1. Get all snapshots from the last 30 minutes for this shift
        2. Calculate average total_orders
        3. If current total_orders > avg * 1.5, trigger queue_surge
        
        Returns:
            list of alert dicts
        """
        pass
    
    @staticmethod
    def _check_inventory_levels(snapshot):
        """
        Check each tracked inventory item against the 20% par threshold.
        
        Returns:
            list of alert dicts (one per item below threshold)
        """
        pass
    
    @staticmethod
    def _check_labor_balance(snapshot):
        """
        Check staff-to-order ratio by station.
        
        If orders_per_kitchen_staff > threshold, alert as labor_imbalance.
        
        Returns:
            list of alert dicts
        """
        pass
    
    @staticmethod
    def _apply_state_machine(new_alerts, shift_id):
        """
        Implement the 2-snapshot persistence rule from the Design Doc.
        
        Logic:
        1. For each new alert, check if a similar alert was triggered
           in the previous snapshot evaluation
        2. If yes (persisted for 2 snapshots) → create as active alert
        3. If no (first occurrence) → store as triggered but don't show yet
        
        For simplicity in MVP: skip the state machine and create alerts
        immediately, but add a comment noting the production behavior.
        
        Also check existing active alerts — if the triggering condition
        has been normal for 3 consecutive snapshots, auto-resolve:
        set is_acknowledged = True, acknowledged_by = None (system),
        add a note that it was auto-resolved.
        """
        pass
    
    @staticmethod
    def _enforce_max_alerts(shift_id):
        """
        If more than MAX_ACTIVE_ALERTS are active, keep only the
        highest-severity ones. Lower-priority alerts stay in DB
        but are not shown.
        
        Severity ranking: critical > warning > info
        """
        pass
```

### Alert Message Templates

**Queue Surge — Critical**:
- Message: "Drive-thru average wait time exceeds 5 minutes. Current avg ticket time: {time}s across {orders} active orders."

**Queue Surge — Warning**:
- Message: "Total order queue is {pct}% above the 30-minute trailing average ({current} orders vs {avg} avg)."

**Stockout Risk — Warning**:
- Message: "{item} at {pct}% of daily par level ({current} {unit} remaining). Estimated depletion in {est_minutes} minutes at current rate."

**Stockout Risk — Info**:
- Message: "{item} below 30% par ({current} {unit} of {par} {unit}). No immediate risk but monitoring recommended."

**Labor Imbalance — Critical**:
- Message: "Kitchen understaffed: {kitchen_staff} staff handling {orders}+ orders/hr (ratio: {ratio}:1, threshold: {threshold}:1)."

**Labor Imbalance — Warning**:
- Message: "Front counter overstaffed relative to current demand. {front_staff} staff for {dine_in} dine-in orders (consider rebalancing)."

---

## Trigger Endpoint

Create an API endpoint to manually trigger evaluation (for development/demo purposes):

### POST `/api/dashboard/evaluate`
**Location**: `app/api/dashboard.py`
**Access**: Admin or Manager

```python
@dashboard_bp.route('/evaluate', methods=['POST'])
@role_required('admin', 'manager')
def trigger_evaluation():
    """
    Manually trigger forecast + recommendation + alert evaluation
    for the current active shift. In production, this runs automatically
    via Celery every 30-60 seconds.
    """
    from flask_jwt_extended import get_jwt
    claims = get_jwt()
    restaurant_id = claims['restaurant_id']
    
    # 1. Get active shift
    # 2. Get latest snapshot
    # 3. Run ForecastService.forecast_demand()
    # 4. Run RecommendationEngine.evaluate()
    # 5. Run AlertService.evaluate()
    # 6. Return results summary
    
    return jsonify({
        'forecast': forecast_result,
        'new_recommendations': [r.to_dict() for r in new_recs],
        'new_alerts': [a.to_dict() for a in new_alerts],
    }), 200
```

---

## Verification Checklist

1. **Forecast produces reasonable predictions**:
   ```bash
   python -c "
   from app import create_app
   from app.services.forecast_service import ForecastService
   from app.models import Shift
   app = create_app('development')
   with app.app_context():
       shift = Shift.query.filter_by(status='active').first()
       if shift:
           result = ForecastService.forecast_demand(shift.shift_id)
           print(f'Forecast: {result}')
           assert result['predicted_total_orders'] > 0
   "
   ```

2. **Recommendation engine generates recommendations from peak data**:
   ```bash
   python -c "
   from app import create_app
   from app.services.recommendation_engine import RecommendationEngine
   from app.models import Shift, OperationalSnapshot
   app = create_app('development')
   with app.app_context():
       shift = Shift.query.filter_by(status='active').first()
       snapshot = OperationalSnapshot.query.filter_by(shift_id=shift.shift_id).order_by(OperationalSnapshot.captured_at.desc()).first()
       recs = RecommendationEngine.evaluate(shift.shift_id, snapshot.snapshot_id)
       print(f'Generated {len(recs)} recommendations')
       for r in recs:
           print(f'  [{r.priority}] {r.title}')
   "
   ```

3. **Alert service detects threshold violations**:
   - Run against a snapshot with high ticket time → should generate ticket_time alert
   - Run against a snapshot with low inventory → should generate stockout_risk alert

4. **Trigger endpoint works via curl**:
   ```bash
   curl -X POST http://localhost:5000/api/dashboard/evaluate \
     -H "Authorization: Bearer <manager_token>" \
     -H "Content-Type: application/json"
   ```

5. **No duplicate recommendations**: Running evaluate twice on the same snapshot should not create duplicate recommendations

6. **All generated records have valid foreign keys** and proper timestamps

## What NOT To Do

- Do NOT implement full ARIMA/XGBoost — use weighted moving average for MVP
- Do NOT implement Celery task scheduling (that's a future enhancement)
- Do NOT build the frontend
- Do NOT modify the database models
- Do NOT change the seed data
- Keep the algorithms simple but functional — correctness over sophistication
