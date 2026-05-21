"""Dashboard service - current state, metrics, and trend aggregation."""
from datetime import datetime, timedelta

from sqlalchemy import case

from app.extensions import db
from app.models import Restaurant, Shift, OperationalSnapshot, Recommendation, Alert


class DashboardService:
    @staticmethod
    def get_current_dashboard(restaurant_id):
        restaurant = db.session.get(Restaurant, restaurant_id) if restaurant_id else None
        if not restaurant:
            return {'error': 'Not found', 'message': 'Restaurant not found', 'status_code': 404}

        shift = Shift.query.filter_by(
            restaurant_id=restaurant_id, status='active'
        ).first()

        if not shift:
            return {'error': 'Not found', 'message': 'No active shift found', 'status_code': 404}

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

        return {
            'restaurant': restaurant.to_dict(),
            'current_shift': shift.to_dict(),
            'latest_snapshot': latest_snapshot.to_dict() if latest_snapshot else None,
            'active_recommendations': [r.to_dict() for r in active_recs],
            'active_alerts': [a.to_dict() for a in active_alerts],
            'summary': summary,
        }

    @staticmethod
    def get_shift_metrics(shift_id, minutes=60):
        shift = db.session.get(Shift, shift_id)
        if not shift:
            return {'error': 'Not found', 'message': 'Shift not found', 'status_code': 404}

        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        snapshots = OperationalSnapshot.query.filter(
            OperationalSnapshot.shift_id == shift_id,
            OperationalSnapshot.captured_at >= cutoff,
        ).order_by(OperationalSnapshot.captured_at).all()

        return {
            'shift_id': shift_id,
            'time_range_minutes': minutes,
            'snapshots': [
                {
                    'captured_at': s.captured_at.isoformat() if s.captured_at else None,
                    'total_orders': s.total_orders,
                    'avg_ticket_time_sec': s.avg_ticket_time_sec,
                    'staff_count': s.staff_count,
                    'dine_in_orders': s.dine_in_orders,
                    'drive_thru_orders': s.drive_thru_orders,
                    'pickup_orders': s.pickup_orders,
                    'delivery_orders': s.delivery_orders,
                }
                for s in snapshots
            ],
        }

    @staticmethod
    def get_trends(restaurant_id, days=7):
        cutoff = datetime.utcnow() - timedelta(days=days)
        shifts = Shift.query.filter(
            Shift.restaurant_id == restaurant_id,
            Shift.shift_date >= cutoff.date(),
        ).order_by(Shift.shift_date).all()

        daily_data = {}
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

            recs = shift.recommendations.all()
            daily_data[date_key]['recommendations_generated'] += len(recs)
            for rec in recs:
                accepted = rec.actions.filter_by(response_type='accepted').count()
                daily_data[date_key]['recommendations_accepted'] += accepted

        result = []
        for date_key in sorted(daily_data.keys()):
            d = daily_data[date_key]
            count = d['snapshot_count'] or 1
            result.append({
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
            'trends': result,
        }
