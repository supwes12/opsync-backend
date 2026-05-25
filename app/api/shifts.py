"""Shifts endpoints - list, detail, create, update shifts."""
from datetime import datetime, date, timezone

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt

from sqlalchemy import func

from app.extensions import db
from app.models import Shift, OperationalSnapshot, Recommendation, RecommendationAction, Alert, Restaurant
from app.utils.decorators import role_required

shifts_bp = Blueprint('shifts', __name__)
shifts_bp.strict_slashes = False


@shifts_bp.route('/', methods=['GET'])
@jwt_required()
def list_shifts():
    claims = get_jwt()
    restaurant_id = request.args.get('restaurant_id', claims.get('restaurant_id'))

    query = Shift.query.filter_by(restaurant_id=restaurant_id)

    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)

    shift_type = request.args.get('shift_type')
    if shift_type:
        query = query.filter_by(shift_type=shift_type)

    date_filter = request.args.get('date')
    if date_filter:
        try:
            d = date.fromisoformat(date_filter)
            query = query.filter_by(shift_date=d)
        except ValueError:
            return jsonify({'error': 'Bad request', 'message': 'Invalid date format. Use YYYY-MM-DD'}), 400

    limit = request.args.get('limit', type=int)

    shifts = query.order_by(Shift.shift_date.desc(), Shift.start_time.desc())
    if limit and limit > 0:
        shifts = shifts.limit(limit)
    shifts = shifts.all()

    # Include restaurant name for display
    restaurant = db.session.get(Restaurant, restaurant_id) if restaurant_id else None
    restaurant_name = restaurant.name if restaurant else None

    results = []
    for s in shifts:
        d = s.to_dict()
        d['restaurant_name'] = restaurant_name
        results.append(d)

    return jsonify({'shifts': results}), 200


@shifts_bp.route('/<shift_id>', methods=['GET'])
@jwt_required()
def get_shift(shift_id):
    shift = db.session.get(Shift, shift_id)
    if not shift:
        return jsonify({'error': 'Not found', 'message': 'Shift not found'}), 404

    shift_dict = shift.to_dict()
    shift_dict['snapshot_count'] = shift.snapshots.count()
    shift_dict['recommendation_count'] = shift.recommendations.count()

    return jsonify({'shift': shift_dict}), 200


@shifts_bp.route('/', methods=['POST'])
@role_required('admin', 'manager')
def create_shift():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Bad request', 'message': 'Request body is required'}), 400

    required = ['restaurant_id', 'shift_date', 'start_time', 'end_time', 'shift_type']
    for field in required:
        if not data.get(field):
            return jsonify({'error': 'Validation error', 'message': f'{field} is required'}), 400

    try:
        shift_date = date.fromisoformat(data['shift_date'])
        start_time = datetime.fromisoformat(data['start_time'])
        end_time = datetime.fromisoformat(data['end_time'])
    except (ValueError, TypeError):
        return jsonify({'error': 'Validation error', 'message': 'Invalid date/time format'}), 400

    shift = Shift(
        restaurant_id=data['restaurant_id'],
        shift_date=shift_date,
        start_time=start_time,
        end_time=end_time,
        shift_type=data['shift_type'],
        manager_id=data.get('manager_id'),
    )

    db.session.add(shift)
    db.session.commit()

    return jsonify({'shift': shift.to_dict()}), 201


@shifts_bp.route('/<shift_id>', methods=['PUT'])
@role_required('admin', 'manager')
def update_shift(shift_id):
    shift = db.session.get(Shift, shift_id)
    if not shift:
        return jsonify({'error': 'Not found', 'message': 'Shift not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Bad request', 'message': 'Request body is required'}), 400

    if 'status' in data:
        if data['status'] not in ('active', 'completed', 'cancelled'):
            return jsonify({'error': 'Validation error', 'message': 'Invalid status'}), 400
        shift.status = data['status']

    if 'manager_id' in data:
        shift.manager_id = data['manager_id']

    if 'shift_type' in data:
        shift.shift_type = data['shift_type']

    if 'start_time' in data:
        try:
            shift.start_time = datetime.fromisoformat(data['start_time'])
        except (ValueError, TypeError):
            return jsonify({'error': 'Validation error', 'message': 'Invalid start_time format'}), 400

    if 'end_time' in data:
        try:
            shift.end_time = datetime.fromisoformat(data['end_time'])
        except (ValueError, TypeError):
            return jsonify({'error': 'Validation error', 'message': 'Invalid end_time format'}), 400

    db.session.commit()

    return jsonify({'shift': shift.to_dict()}), 200


@shifts_bp.route('/<shift_id>/summary', methods=['GET'])
@jwt_required()
def get_shift_summary(shift_id):
    """Return a post-shift summary with aggregated metrics."""
    shift = db.session.get(Shift, shift_id)
    if not shift:
        return jsonify({'error': 'Not found', 'message': 'Shift not found'}), 404

    # --- Snapshot aggregates ---
    snapshot_agg = db.session.query(
        func.count(OperationalSnapshot.snapshot_id).label('snapshot_count'),
        func.sum(OperationalSnapshot.total_orders).label('total_orders'),
        func.avg(OperationalSnapshot.avg_ticket_time_sec).label('avg_ticket_time'),
        func.max(OperationalSnapshot.total_orders).label('peak_orders'),
        func.avg(OperationalSnapshot.staff_count).label('staff_count_avg'),
    ).filter(
        OperationalSnapshot.shift_id == shift_id
    ).first()

    total_orders = int(snapshot_agg.total_orders or 0)
    avg_ticket_time = round(float(snapshot_agg.avg_ticket_time or 0), 1)
    peak_orders = int(snapshot_agg.peak_orders or 0)
    staff_count_avg = round(float(snapshot_agg.staff_count_avg or 0), 1)

    # --- Recommendation counts ---
    recommendations_generated = Recommendation.query.filter_by(
        shift_id=shift_id
    ).count()

    # Count actions by response_type for recommendations in this shift
    action_counts = (
        db.session.query(
            RecommendationAction.response_type,
            func.count(RecommendationAction.action_id).label('cnt'),
        )
        .join(Recommendation, RecommendationAction.recommendation_id == Recommendation.recommendation_id)
        .filter(Recommendation.shift_id == shift_id)
        .group_by(RecommendationAction.response_type)
        .all()
    )
    action_map = {row.response_type: row.cnt for row in action_counts}
    recommendations_accepted = action_map.get('accepted', 0)
    recommendations_deferred = action_map.get('deferred', 0)
    recommendations_rejected = action_map.get('rejected', 0)

    # --- Alert counts ---
    alerts_triggered = Alert.query.filter_by(shift_id=shift_id).count()
    alerts_acknowledged = Alert.query.filter_by(
        shift_id=shift_id, is_acknowledged=True
    ).count()

    # --- Restaurant name ---
    restaurant = db.session.get(Restaurant, shift.restaurant_id)
    restaurant_name = restaurant.name if restaurant else None

    return jsonify({
        'shift_info': {
            'shift_id': shift.shift_id,
            'restaurant_id': shift.restaurant_id,
            'restaurant_name': restaurant_name,
            'shift_date': shift.shift_date.isoformat() if shift.shift_date else None,
            'start_time': shift.start_time.isoformat() if shift.start_time else None,
            'end_time': shift.end_time.isoformat() if shift.end_time else None,
            'shift_type': shift.shift_type,
            'status': shift.status,
        },
        'total_orders': total_orders,
        'avg_ticket_time': avg_ticket_time,
        'peak_orders': peak_orders,
        'staff_count_avg': staff_count_avg,
        'recommendations_generated': recommendations_generated,
        'recommendations_accepted': recommendations_accepted,
        'recommendations_deferred': recommendations_deferred,
        'recommendations_rejected': recommendations_rejected,
        'alerts_triggered': alerts_triggered,
        'alerts_acknowledged': alerts_acknowledged,
    }), 200
