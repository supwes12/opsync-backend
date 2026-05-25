"""Dashboard service - current state, metrics, and trend aggregation."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import case

from app.extensions import db
from app.models import Restaurant, Shift, OperationalSnapshot, Recommendation, Alert


class DashboardService:
    @staticmethod
    def get_current_dashboard(restaurant_id, shift_id=None):
        restaurant = db.session.get(Restaurant, restaurant_id) if restaurant_id else None
        if not restaurant:
            return {'error': 'Not found', 'message': 'Restaurant not found', 'status_code': 404}

        if shift_id:
            shift = db.session.get(Shift, shift_id)
            if not shift:
                return {'error': 'Not found', 'message': 'Shift not found', 'status_code': 404}
        else:
            shift = Shift.query.filter_by(
                restaurant_id=restaurant_id, status='active'
            ).first()

        if not shift:
            # Return a graceful empty state instead of a 404 so the
            # frontend can render a "no active shift" message without crashing.
            return {
                'restaurant': restaurant.to_dict(),
                'active_shift': None,
                'latest_snapshot': None,
                'recent_recommendations': [],
                'active_alerts': [],
                'summary': {
                    'total_orders': 0,
                    'avg_ticket_time_sec': 0,
                    'staff_count': 0,
                    'unacknowledged_alerts': 0,
                    'pending_recommendations': 0,
                },
                'forecast': {
                    'predicted_orders_30min': 0,
                    'predicted_orders_60min': 0,
                    'confidence': 'none',
                },
            }

        latest_snapshot = OperationalSnapshot.query.filter_by(
            shift_id=shift.shift_id
        ).order_by(OperationalSnapshot.captured_at.desc()).first()

        priority_order = case(
            (Recommendation.priority == 'high', 1),
            (Recommendation.priority == 'medium', 2),
            (Recommendation.priority == 'low', 3),
            else_=4,
        )
        active_recs = Recommendation.query.filter_by(
            shift_id=shift.shift_id, is_active=True
        ).order_by(priority_order, Recommendation.created_at.desc()).all()

        severity_order = case(
            (Alert.severity == 'critical', 1),
            (Alert.severity == 'warning', 2),
            (Alert.severity == 'info', 3),
            else_=4,
        )
        active_alerts = Alert.query.filter_by(
            shift_id=shift.shift_id, is_acknowledged=False
        ).order_by(severity_order, Alert.created_at.desc()).all()

        summary = {
            'total_orders': latest_snapshot.total_orders if latest_snapshot else 0,
            'avg_ticket_time_sec': latest_snapshot.avg_ticket_time_sec if latest_snapshot else 0,
            'staff_count': latest_snapshot.staff_count if latest_snapshot else 0,
            'unacknowledged_alerts': len(active_alerts),
            'pending_recommendations': len(active_recs),
        }

        # Task 5: Include forecast data from ForecastService
        from app.services.forecast_service import ForecastService
        forecast_raw = ForecastService.forecast_demand(shift.shift_id, horizon_minutes=30)
        forecast_60 = ForecastService.forecast_demand(shift.shift_id, horizon_minutes=60)

        forecast = {
            'predicted_orders_30min': forecast_raw.get('predicted_total_orders', 0),
            'predicted_orders_60min': forecast_60.get('predicted_total_orders', 0),
            'confidence': forecast_raw.get('confidence', 'low'),
        }

        return {
            'restaurant': restaurant.to_dict(),
            'active_shift': shift.to_dict(),
            'latest_snapshot': latest_snapshot.to_dict() if latest_snapshot else None,
            'recent_recommendations': [r.to_dict() for r in active_recs],
            'active_alerts': [a.to_dict() for a in active_alerts],
            'summary': summary,
            'forecast': forecast,
        }

    @staticmethod
    def get_shift_metrics(shift_id, minutes=60):
        shift = db.session.get(Shift, shift_id)
        if not shift:
            return {'error': 'Not found', 'message': 'Shift not found', 'status_code': 404}

        # Use naive datetime for cutoff to match DB storage (SQLite stores naive)
        cutoff = datetime.now() - timedelta(minutes=minutes)
        snapshots = OperationalSnapshot.query.filter(
            OperationalSnapshot.shift_id == shift_id,
            OperationalSnapshot.captured_at >= cutoff,
        ).order_by(OperationalSnapshot.captured_at).all()

        # If the time-based filter returns too few snapshots, fall back to
        # returning ALL snapshots for this shift so charts always have data.
        if len(snapshots) < 5:
            snapshots = OperationalSnapshot.query.filter(
                OperationalSnapshot.shift_id == shift_id,
            ).order_by(OperationalSnapshot.captured_at).all()

        # Build chart-friendly format
        orders_over_time = []
        avg_ticket_time_trend = []
        staff_utilization = []
        channel_totals = {
            'Drive-Thru': 0,
            'Dine-In': 0,
            'Delivery': 0,
            'Pickup': 0,
        }

        # orders per staff member per snapshot interval at full utilization
        STAFF_CAPACITY_FACTOR = 8

        for s in snapshots:
            ts = s.captured_at.strftime('%H:%M') if s.captured_at else '00:00'

            orders_over_time.append({
                'timestamp': ts,
                'count': s.total_orders or 0,
            })

            avg_ticket_time_trend.append({
                'timestamp': ts,
                'seconds': s.avg_ticket_time_sec or 0,
            })

            staff = max(s.staff_count, 1) if s.staff_count else 1
            ratio = min(1.0, round((s.total_orders or 0) / (staff * STAFF_CAPACITY_FACTOR), 2))
            staff_utilization.append({
                'timestamp': ts,
                'ratio': ratio,
            })

            channel_totals['Drive-Thru'] += (s.drive_thru_orders or 0)
            channel_totals['Dine-In'] += (s.dine_in_orders or 0)
            channel_totals['Delivery'] += (s.delivery_orders or 0)
            channel_totals['Pickup'] += (s.pickup_orders or 0)

        channel_breakdown = [
            {'channel': channel, 'count': count}
            for channel, count in channel_totals.items()
        ]

        return {
            'shift_id': shift_id,
            'time_range_minutes': minutes,
            'orders_over_time': orders_over_time,
            'channel_breakdown': channel_breakdown,
            'avg_ticket_time_trend': avg_ticket_time_trend,
            'staff_utilization': staff_utilization,
        }

    @staticmethod
    def get_trends(restaurant_id, days=7, shift_id=None):
        cutoff = datetime.now() - timedelta(days=days)
        query = Shift.query.filter(
            Shift.restaurant_id == restaurant_id,
            Shift.shift_date >= cutoff.date(),
        )
        if shift_id:
            query = query.filter(Shift.shift_id == shift_id)
        shifts = query.order_by(Shift.shift_date).all()

        daily_data = {}
        all_ticket_times = []
        alert_counts = {}
        total_recs_generated = 0
        total_recs_accepted = 0
        staff_by_hour = {}  # {hour: [staff_counts...]}

        for shift in shifts:
            date_key = shift.shift_date.isoformat()
            if date_key not in daily_data:
                daily_data[date_key] = {
                    'date': date_key,
                    'total_orders': 0,
                    'ticket_time_sum': 0,
                    'snapshot_count': 0,
                    'staff_sum': 0,
                    'recommendations_generated': 0,
                    'recommendations_accepted': 0,
                }

            snapshots = shift.snapshots.all()
            for s in snapshots:
                daily_data[date_key]['total_orders'] += s.total_orders
                daily_data[date_key]['ticket_time_sum'] += (s.avg_ticket_time_sec or 0)
                daily_data[date_key]['snapshot_count'] += 1
                daily_data[date_key]['staff_sum'] += s.staff_count

                # Collect ticket times for distribution
                if s.avg_ticket_time_sec:
                    all_ticket_times.append(s.avg_ticket_time_sec)

                # Staff utilization heatmap: group by hour
                if s.captured_at:
                    hour_key = s.captured_at.strftime('%H:00')
                    if hour_key not in staff_by_hour:
                        staff_by_hour[hour_key] = []
                    staff_count = max(s.staff_count, 1) if s.staff_count else 1
                    ratio = min(1.0, round((s.total_orders or 0) / (staff_count * 8), 2))
                    staff_by_hour[hour_key].append(ratio)

            recs = shift.recommendations.all()
            daily_data[date_key]['recommendations_generated'] += len(recs)
            total_recs_generated += len(recs)
            for rec in recs:
                accepted = rec.actions.filter_by(response_type='accepted').count()
                daily_data[date_key]['recommendations_accepted'] += accepted
                total_recs_accepted += accepted

            # Count alerts by type
            alerts = shift.alerts.all()
            for alert in alerts:
                alert_type = alert.alert_type
                if alert_type not in alert_counts:
                    alert_counts[alert_type] = 0
                alert_counts[alert_type] += 1

        # Build order_volume_by_day
        order_volume_by_day = []
        for date_key in sorted(daily_data.keys()):
            d = daily_data[date_key]
            order_volume_by_day.append({
                'date': d['date'],
                'total_orders': d['total_orders'],
            })

        # Build ticket_time_distribution (bucketed)
        ticket_buckets = {
            '0-60s': 0, '61-120s': 0, '121-180s': 0,
            '181-240s': 0, '241-300s': 0, '300s+': 0,
        }
        for t in all_ticket_times:
            if t <= 60:
                ticket_buckets['0-60s'] += 1
            elif t <= 120:
                ticket_buckets['61-120s'] += 1
            elif t <= 180:
                ticket_buckets['121-180s'] += 1
            elif t <= 240:
                ticket_buckets['181-240s'] += 1
            elif t <= 300:
                ticket_buckets['241-300s'] += 1
            else:
                ticket_buckets['300s+'] += 1

        ticket_time_distribution = [
            {'bucket': bucket, 'count': count}
            for bucket, count in ticket_buckets.items()
        ]

        # Build staff_utilization_heatmap
        staff_utilization_heatmap = []
        for hour_key in sorted(staff_by_hour.keys()):
            ratios = staff_by_hour[hour_key]
            avg_ratio = round(sum(ratios) / len(ratios), 2) if ratios else 0
            staff_utilization_heatmap.append({
                'hour': hour_key,
                'avg_utilization': avg_ratio,
                'sample_count': len(ratios),
            })

        # Build recommendation_acceptance_rate
        recommendation_acceptance_rate = round(
            (total_recs_accepted / total_recs_generated * 100) if total_recs_generated > 0 else 0, 1
        )

        # Build alert_frequency
        alert_frequency = [
            {'type': alert_type, 'count': count}
            for alert_type, count in sorted(alert_counts.items(), key=lambda x: -x[1])
        ]

        # Build legacy trends array
        trends = []
        for date_key in sorted(daily_data.keys()):
            d = daily_data[date_key]
            count = d['snapshot_count'] or 1
            trends.append({
                'date': d['date'],
                'total_orders': d['total_orders'],
                'avg_ticket_time_sec': round(d['ticket_time_sum'] / count),
                'avg_staff_count': round(d['staff_sum'] / count, 1),
                'recommendations_generated': d['recommendations_generated'],
                'recommendations_accepted': d['recommendations_accepted'],
            })

        return {
            'restaurant_id': restaurant_id,
            'days': days,
            'trends': trends,
            'order_volume_by_day': order_volume_by_day,
            'ticket_time_distribution': ticket_time_distribution,
            'staff_utilization_heatmap': staff_utilization_heatmap,
            'recommendation_acceptance_rate': recommendation_acceptance_rate,
            'alert_frequency': alert_frequency,
        }
