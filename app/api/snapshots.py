"""Snapshots endpoints - data ingestion from external POS/IoT systems."""
from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt

from app.extensions import db
from app.models.operational_snapshot import OperationalSnapshot
from app.models.shift import Shift

snapshots_bp = Blueprint('snapshots', __name__)
snapshots_bp.strict_slashes = False


@snapshots_bp.route('/', methods=['POST'])
@jwt_required()
def create_snapshot():
    claims = get_jwt()
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Bad request', 'message': 'Request body is required'}), 400

    # Determine shift_id: explicit or auto-detect from restaurant
    shift_id = data.get('shift_id')
    if not shift_id:
        restaurant_id = data.get('restaurant_id', claims.get('restaurant_id'))
        if not restaurant_id:
            return jsonify({'error': 'Bad request', 'message': 'shift_id or restaurant_id is required'}), 400
        shift = Shift.query.filter_by(restaurant_id=restaurant_id, status='active').first()
        if not shift:
            return jsonify({'error': 'Not found', 'message': 'No active shift found'}), 404
        shift_id = shift.shift_id
    else:
        shift = db.session.get(Shift, shift_id)
        if not shift:
            return jsonify({'error': 'Not found', 'message': 'Shift not found'}), 404

    # Validate required fields
    total_orders = data.get('total_orders')
    staff_count = data.get('staff_count')
    if total_orders is None or staff_count is None:
        return jsonify({
            'error': 'Bad request',
            'message': 'total_orders and staff_count are required',
        }), 400

    try:
        total_orders = int(total_orders)
        staff_count = int(staff_count)
    except (ValueError, TypeError):
        return jsonify({'error': 'Bad request', 'message': 'total_orders and staff_count must be integers'}), 400

    if total_orders < 0 or staff_count < 0:
        return jsonify({'error': 'Bad request', 'message': 'total_orders and staff_count must be non-negative'}), 400

    # Parse captured_at or default to now
    captured_at_str = data.get('captured_at')
    if captured_at_str:
        try:
            captured_at = datetime.fromisoformat(captured_at_str)
        except (ValueError, TypeError):
            return jsonify({'error': 'Bad request', 'message': 'Invalid captured_at format. Use ISO 8601.'}), 400
    else:
        captured_at = datetime.now()

    snapshot = OperationalSnapshot(
        shift_id=shift_id,
        captured_at=captured_at,
        total_orders=total_orders,
        dine_in_orders=data.get('dine_in_orders'),
        drive_thru_orders=data.get('drive_thru_orders'),
        pickup_orders=data.get('pickup_orders'),
        delivery_orders=data.get('delivery_orders'),
        avg_ticket_time_sec=data.get('avg_ticket_time_sec'),
        staff_count=staff_count,
        kitchen_staff=data.get('kitchen_staff'),
        front_staff=data.get('front_staff'),
    )

    # Set inventory if provided
    inventory = data.get('inventory')
    if inventory:
        snapshot.inventory = inventory

    db.session.add(snapshot)
    db.session.commit()

    return jsonify({'snapshot': snapshot.to_dict()}), 201
