"""Recommendation generation - labor optimization based on demand vs staffing."""
import math
from datetime import datetime, timezone

from app.extensions import db
from app.models.operational_snapshot import OperationalSnapshot
from app.models.recommendation import Recommendation
from app.models.shift import Shift
from app.services.forecast_service import ForecastService


class RecommendationEngine:
    """
    Generates operational recommendations by comparing current state
    against optimal state derived from demand forecasts.
    """

    KITCHEN_RATIO = 8
    FRONT_RATIO = 12
    MIN_KITCHEN_STAFF = 2
    MIN_FRONT_STAFF = 1
    INVENTORY_CRITICAL = 0.15
    INVENTORY_WARNING = 0.30
    MAX_ACTIVE_RECS = 5

    @staticmethod
    def evaluate(shift_id, snapshot_id):
        snapshot = db.session.get(OperationalSnapshot, snapshot_id)
        shift = db.session.get(Shift, shift_id)
        if not snapshot or not shift:
            return []

        forecast = ForecastService.forecast_demand(shift_id)

        candidates = []
        candidates.extend(RecommendationEngine._check_labor(snapshot, forecast))
        candidates.extend(RecommendationEngine._check_inventory(snapshot))
        candidates.extend(RecommendationEngine._check_prep_timing(snapshot, shift))

        new_recs = RecommendationEngine._deduplicate(candidates, shift_id)

        active_count = Recommendation.query.filter_by(
            shift_id=shift_id, is_active=True
        ).count()
        slots = max(0, RecommendationEngine.MAX_ACTIVE_RECS - active_count)

        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        new_recs.sort(key=lambda r: priority_order.get(r['priority'], 3))
        new_recs = new_recs[:slots] if slots > 0 else []

        created = []
        for rec_data in new_recs:
            rec = Recommendation(
                shift_id=shift_id,
                snapshot_id=snapshot_id,
                rec_type=rec_data['rec_type'],
                priority=rec_data['priority'],
                title=rec_data['title'],
                description=rec_data['description'],
                rationale=rec_data['rationale'],
                suggested_action=rec_data['suggested_action'],
            )
            db.session.add(rec)
            created.append(rec)

        if created:
            db.session.commit()

        return created

    @staticmethod
    def _check_labor(snapshot, forecast):
        recs = []
        predicted_orders = forecast.get('predicted_total_orders', 0)
        orders_per_hour = predicted_orders * 2

        optimal_kitchen = max(
            RecommendationEngine.MIN_KITCHEN_STAFF,
            math.ceil(orders_per_hour / RecommendationEngine.KITCHEN_RATIO)
        )
        optimal_front = max(
            RecommendationEngine.MIN_FRONT_STAFF,
            math.ceil(orders_per_hour / RecommendationEngine.FRONT_RATIO)
        )

        current_kitchen = snapshot.kitchen_staff or 0
        current_front = snapshot.front_staff or 0
        ticket_time = snapshot.avg_ticket_time_sec or 0

        kitchen_gap = optimal_kitchen - current_kitchen
        if kitchen_gap >= 1:
            gap_norm = min(100, kitchen_gap * 25)
            demand_norm = min(100, orders_per_hour)
            ticket_norm = min(100, max(0, (ticket_time - 120) / 1.8))
            priority = RecommendationEngine._calculate_priority(gap_norm, demand_norm, ticket_norm)

            recs.append({
                'rec_type': 'labor_kitchen',
                'priority': priority,
                'title': f'Move {kitchen_gap} staff from front to kitchen',
                'description': (
                    f'Kitchen is handling {snapshot.total_orders} orders with only '
                    f'{current_kitchen} staff. Optimal staffing for current demand is {optimal_kitchen}.'
                ),
                'rationale': (
                    f'Average ticket time has increased to {ticket_time}s, which exceeds the 180s target. '
                    f'Demand forecast predicts {predicted_orders} orders in the next 30 minutes.'
                ),
                'suggested_action': (
                    f'Reassign {kitchen_gap} front-of-house staff to kitchen stations. '
                    f'Priority: grill station first, then prep.'
                ),
            })

        front_surplus = current_front - optimal_front
        if front_surplus >= 2:
            recs.append({
                'rec_type': 'labor_front',
                'priority': 'low',
                'title': f'Rotate {front_surplus} front counter staff to break',
                'description': (
                    f'Front counter has {current_front} staff but current dine-in volume '
                    f'only requires {optimal_front}.'
                ),
                'rationale': (
                    f'Order volume has decreased to {snapshot.total_orders} total. '
                    f'{front_surplus} front staff can take scheduled breaks without impacting service.'
                ),
                'suggested_action': (
                    f'Send {front_surplus} staff on break rotation. '
                    f'Maintain {RecommendationEngine.MIN_FRONT_STAFF} at counter minimum.'
                ),
            })

        return recs

    @staticmethod
    def _check_inventory(snapshot):
        recs = []
        inventory = snapshot.inventory
        if not inventory:
            return recs

        for item_name, item_data in inventory.items():
            if isinstance(item_data, dict):
                current = item_data.get('current', 0)
                par = item_data.get('par', 1)
                unit = item_data.get('unit', 'units')
            else:
                continue

            if par <= 0:
                continue

            pct = current / par

            if pct < RecommendationEngine.INVENTORY_CRITICAL:
                est_minutes = 'unknown'
                recs.append({
                    'rec_type': 'inventory_critical',
                    'priority': 'high',
                    'title': f'{item_name} approaching stockout',
                    'description': (
                        f'{item_name} is at {round(pct * 100)}% of daily par level '
                        f'({current} {unit} remaining of {par} {unit} par).'
                    ),
                    'rationale': (
                        f'At current consumption rate, {item_name} will run out in '
                        f'approximately {est_minutes} minutes.'
                    ),
                    'suggested_action': (
                        f'Place emergency restock order or begin substitution protocol '
                        f'for affected menu items.'
                    ),
                })
            elif pct < RecommendationEngine.INVENTORY_WARNING:
                recs.append({
                    'rec_type': 'inventory_warning',
                    'priority': 'medium',
                    'title': f'{item_name} below reorder threshold',
                    'description': f'{item_name} is at {round(pct * 100)}% of daily par level.',
                    'rationale': (
                        f'Current usage pattern suggests this item may reach critical levels '
                        f'before shift end.'
                    ),
                    'suggested_action': (
                        f'Monitor closely and consider preemptive restock if consumption rate increases.'
                    ),
                })

        return recs

    @staticmethod
    def _check_prep_timing(snapshot, shift):
        recs = []
        now = datetime.now(timezone.utc)
        end_time = shift.end_time

        if not end_time:
            return recs

        if end_time.tzinfo is None:
            from datetime import timezone as tz
            end_time_aware = end_time.replace(tzinfo=tz.utc)
        else:
            end_time_aware = end_time

        minutes_to_end = (end_time_aware - now).total_seconds() / 60

        if 0 < minutes_to_end <= 60:
            next_shift = (
                Shift.query
                .filter_by(restaurant_id=shift.restaurant_id)
                .filter(Shift.start_time >= shift.end_time)
                .order_by(Shift.start_time.asc())
                .first()
            )

            if next_shift:
                recs.append({
                    'rec_type': 'prep_next_shift',
                    'priority': 'medium',
                    'title': f'Start prepping for {next_shift.shift_type} shift',
                    'description': (
                        f'Current shift ends in {round(minutes_to_end)} minutes. '
                        f'{next_shift.shift_type} shift starts at '
                        f'{next_shift.start_time.strftime("%H:%M") if next_shift.start_time else "N/A"}.'
                    ),
                    'rationale': 'Prep items for the upcoming shift should be started now to ensure readiness.',
                    'suggested_action': (
                        f'Begin prep checklist for {next_shift.shift_type}: '
                        f'restock stations, prep ingredients, clean work areas.'
                    ),
                })

        return recs

    @staticmethod
    def _calculate_priority(gap_magnitude, demand_duration_min, ticket_time_impact):
        score = (gap_magnitude * 0.4) + (demand_duration_min * 0.3) + (ticket_time_impact * 0.3)
        if score >= 70:
            return 'high'
        elif score >= 40:
            return 'medium'
        return 'low'

    @staticmethod
    def _deduplicate(new_recs, shift_id):
        existing = Recommendation.query.filter_by(
            shift_id=shift_id, is_active=True
        ).all()

        existing_keys = {(r.rec_type, r.title) for r in existing}

        return [r for r in new_recs if (r['rec_type'], r['title']) not in existing_keys]
