"""Demand forecasting - weighted moving average for order volume prediction."""
from datetime import datetime, timezone

from app.extensions import db
from app.models.operational_snapshot import OperationalSnapshot
from app.models.shift import Shift


class ForecastService:
    """
    Short-horizon demand forecasting using weighted moving average.
    Production upgrade path: Replace with ARIMA + XGBoost ensemble.
    """

    WEIGHTS = [0.35, 0.25, 0.20, 0.12, 0.08]

    @staticmethod
    def forecast_demand(shift_id, horizon_minutes=30):
        snapshots = (
            OperationalSnapshot.query
            .filter_by(shift_id=shift_id)
            .order_by(OperationalSnapshot.captured_at.desc())
            .limit(5)
            .all()
        )

        if not snapshots:
            return {
                'predicted_total_orders': 0,
                'predicted_by_channel': {
                    'dine_in': 0, 'drive_thru': 0, 'pickup': 0, 'delivery': 0
                },
                'predicted_avg_ticket_time': 0,
                'confidence': 'low',
                'horizon_minutes': horizon_minutes,
                'generated_at': datetime.now(timezone.utc).isoformat(),
            }

        n = len(snapshots)
        weights = ForecastService.WEIGHTS[:n]
        weight_sum = sum(weights)
        weights = [w / weight_sum for w in weights]

        if n < 3:
            confidence = 'low'
        elif n < 5:
            confidence = 'medium'
        else:
            confidence = 'high'

        def weighted_avg(values):
            return sum(v * w for v, w in zip(values, weights))

        total_orders_vals = [s.total_orders or 0 for s in snapshots]
        dine_in_vals = [s.dine_in_orders or 0 for s in snapshots]
        drive_thru_vals = [s.drive_thru_orders or 0 for s in snapshots]
        pickup_vals = [s.pickup_orders or 0 for s in snapshots]
        delivery_vals = [s.delivery_orders or 0 for s in snapshots]
        ticket_time_vals = [s.avg_ticket_time_sec or 0 for s in snapshots]

        trend = ForecastService._calculate_trend(total_orders_vals)

        horizon_scale = horizon_minutes / 30.0

        predicted_total = max(0, round(weighted_avg(total_orders_vals) * trend * horizon_scale))
        predicted_dine_in = max(0, round(weighted_avg(dine_in_vals) * trend * horizon_scale))
        predicted_drive_thru = max(0, round(weighted_avg(drive_thru_vals) * trend * horizon_scale))
        predicted_pickup = max(0, round(weighted_avg(pickup_vals) * trend * horizon_scale))
        predicted_delivery = max(0, round(weighted_avg(delivery_vals) * trend * horizon_scale))
        predicted_ticket_time = max(0, round(weighted_avg(ticket_time_vals) * trend))

        return {
            'predicted_total_orders': predicted_total,
            'predicted_by_channel': {
                'dine_in': predicted_dine_in,
                'drive_thru': predicted_drive_thru,
                'pickup': predicted_pickup,
                'delivery': predicted_delivery,
            },
            'predicted_avg_ticket_time': predicted_ticket_time,
            'confidence': confidence,
            'horizon_minutes': horizon_minutes,
            'generated_at': datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _calculate_trend(values):
        """Calculate trend multiplier using simple linear regression. Returns 0.8-1.3."""
        n = len(values)
        if n < 2:
            return 1.0

        reversed_vals = list(reversed(values))
        xs = list(range(n))
        sum_x = sum(xs)
        sum_y = sum(reversed_vals)
        sum_xy = sum(x * y for x, y in zip(xs, reversed_vals))
        sum_x2 = sum(x * x for x in xs)

        denom = n * sum_x2 - sum_x * sum_x
        if denom == 0:
            return 1.0

        slope = (n * sum_xy - sum_x * sum_y) / denom
        mean_y = sum_y / n
        if mean_y == 0:
            return 1.0

        normalized_slope = slope / mean_y
        multiplier = 1.0 + normalized_slope
        return max(0.8, min(1.3, multiplier))
