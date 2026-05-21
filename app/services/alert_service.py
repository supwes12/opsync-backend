"""Alert threshold evaluation - ticket time, queue depth, inventory, staffing."""
from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models.alert import Alert
from app.models.operational_snapshot import OperationalSnapshot


class AlertService:
    """
    Evaluates operational snapshots against configurable thresholds
    and generates alerts.

    MVP simplification: alerts are created immediately (no 2-snapshot
    persistence state machine). Production version should require a
    condition to persist for 2 consecutive snapshots before surfacing.
    """

    THRESHOLDS = {
        'ticket_time_warning': 180,
        'ticket_time_critical': 300,
        'queue_surge_pct': 1.50,
        'inventory_critical_pct': 0.20,
        'staff_order_ratio_min': {
            'kitchen': 10,
            'front': 15,
        },
    }

    MAX_ACTIVE_ALERTS = 5

    @staticmethod
    def evaluate(shift_id, snapshot_id):
        snapshot = db.session.get(OperationalSnapshot, snapshot_id)
        if not snapshot:
            return []

        candidates = []
        candidates.extend(AlertService._check_ticket_time(snapshot))
        candidates.extend(AlertService._check_queue_surge(snapshot, shift_id))
        candidates.extend(AlertService._check_inventory_levels(snapshot))
        candidates.extend(AlertService._check_labor_balance(snapshot))

        AlertService._auto_resolve(shift_id, snapshot, candidates)

        existing_types = {
            a.alert_type
            for a in Alert.query.filter_by(shift_id=shift_id, is_acknowledged=False).all()
        }
        candidates = [c for c in candidates if c['alert_type'] not in existing_types]

        created = []
        for alert_data in candidates:
            alert = Alert(
                shift_id=shift_id,
                snapshot_id=snapshot_id,
                alert_type=alert_data['alert_type'],
                severity=alert_data['severity'],
                message=alert_data['message'],
            )
            db.session.add(alert)
            created.append(alert)

        if created:
            db.session.commit()

        AlertService._enforce_max_alerts(shift_id)

        return created

    @staticmethod
    def _check_ticket_time(snapshot):
        alerts = []
        ticket_time = snapshot.avg_ticket_time_sec or 0

        if ticket_time >= AlertService.THRESHOLDS['ticket_time_critical']:
            alerts.append({
                'alert_type': 'ticket_time_critical',
                'severity': 'critical',
                'message': (
                    f'Drive-thru average wait time exceeds 5 minutes. '
                    f'Current avg ticket time: {ticket_time}s across '
                    f'{snapshot.total_orders} active orders.'
                ),
            })
        elif ticket_time >= AlertService.THRESHOLDS['ticket_time_warning']:
            alerts.append({
                'alert_type': 'ticket_time_warning',
                'severity': 'warning',
                'message': (
                    f'Average ticket time is {ticket_time}s, exceeding the '
                    f'{AlertService.THRESHOLDS["ticket_time_warning"]}s warning threshold. '
                    f'Monitor closely to prevent further degradation.'
                ),
            })

        return alerts

    @staticmethod
    def _check_queue_surge(snapshot, shift_id):
        alerts = []
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)

        trailing_snapshots = (
            OperationalSnapshot.query
            .filter_by(shift_id=shift_id)
            .filter(OperationalSnapshot.captured_at >= cutoff)
            .filter(OperationalSnapshot.snapshot_id != snapshot.snapshot_id)
            .all()
        )

        if not trailing_snapshots:
            return alerts

        avg_orders = sum(s.total_orders or 0 for s in trailing_snapshots) / len(trailing_snapshots)
        current_orders = snapshot.total_orders or 0

        if avg_orders > 0 and current_orders > avg_orders * AlertService.THRESHOLDS['queue_surge_pct']:
            pct = round((current_orders / avg_orders) * 100)
            alerts.append({
                'alert_type': 'queue_surge',
                'severity': 'warning',
                'message': (
                    f'Total order queue is {pct}% above the 30-minute trailing average '
                    f'({current_orders} orders vs {round(avg_orders)} avg).'
                ),
            })

        return alerts

    @staticmethod
    def _check_inventory_levels(snapshot):
        alerts = []
        inventory = snapshot.inventory
        if not inventory:
            return alerts

        for item_name, item_data in inventory.items():
            if not isinstance(item_data, dict):
                continue

            current = item_data.get('current', 0)
            par = item_data.get('par', 1)
            unit = item_data.get('unit', 'units')

            if par <= 0:
                continue

            pct = current / par
            if pct < AlertService.THRESHOLDS['inventory_critical_pct']:
                alerts.append({
                    'alert_type': 'stockout_risk',
                    'severity': 'warning',
                    'message': (
                        f'{item_name} at {round(pct * 100)}% of daily par level '
                        f'({current} {unit} remaining). '
                        f'Estimated depletion imminent at current rate.'
                    ),
                })

        return alerts

    @staticmethod
    def _check_labor_balance(snapshot):
        alerts = []
        kitchen_staff = snapshot.kitchen_staff or 0
        front_staff = snapshot.front_staff or 0
        total_orders = snapshot.total_orders or 0
        dine_in = snapshot.dine_in_orders or 0

        thresholds = AlertService.THRESHOLDS['staff_order_ratio_min']

        if kitchen_staff > 0:
            kitchen_ratio = total_orders / kitchen_staff
            if kitchen_ratio > thresholds['kitchen']:
                alerts.append({
                    'alert_type': 'labor_imbalance',
                    'severity': 'critical',
                    'message': (
                        f'Kitchen understaffed: {kitchen_staff} staff handling {total_orders}+ '
                        f'orders/hr (ratio: {round(kitchen_ratio, 1)}:1, '
                        f'threshold: {thresholds["kitchen"]}:1).'
                    ),
                })

        if front_staff > 0 and dine_in > 0:
            front_ratio = dine_in / front_staff
            if front_ratio < 2 and front_staff >= 3:
                alerts.append({
                    'alert_type': 'labor_overstaffed_front',
                    'severity': 'info',
                    'message': (
                        f'Front counter overstaffed relative to current demand. '
                        f'{front_staff} staff for {dine_in} dine-in orders '
                        f'(consider rebalancing).'
                    ),
                })

        return alerts

    @staticmethod
    def _auto_resolve(shift_id, current_snapshot, current_alerts):
        """Auto-resolve active alerts whose condition has returned to normal."""
        current_alert_types = {a['alert_type'] for a in current_alerts}

        active_alerts = Alert.query.filter_by(
            shift_id=shift_id, is_acknowledged=False
        ).all()

        for alert in active_alerts:
            if alert.alert_type not in current_alert_types:
                alert.is_acknowledged = True
                alert.acknowledged_at = datetime.now(timezone.utc)

        if active_alerts:
            db.session.commit()

    @staticmethod
    def _enforce_max_alerts(shift_id):
        active_alerts = Alert.query.filter_by(
            shift_id=shift_id, is_acknowledged=False
        ).all()

        if len(active_alerts) <= AlertService.MAX_ACTIVE_ALERTS:
            return

        severity_rank = {'critical': 0, 'warning': 1, 'info': 2}
        active_alerts.sort(key=lambda a: (severity_rank.get(a.severity, 3), a.created_at))

        for alert in active_alerts[AlertService.MAX_ACTIVE_ALERTS:]:
            alert.is_acknowledged = True
            alert.acknowledged_at = datetime.now(timezone.utc)

        db.session.commit()
