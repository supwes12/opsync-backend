"""Shifts endpoints - list, detail, create, update shifts."""
from datetime import datetime, date

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt

from app.extensions import db
from app.models import Shift
from app.utils.decorators import role_required

shifts_bp = Blueprint('shifts', __name__)


@shifts_bp.route('/', methods=['GET'])
@jwt_required()
def list_shifts():
    claims = get_jwt()
    restaurant_id = request.args.get('restaurant_id', claims.get('restaurant_id'))

    query = Shift.query.filter_by(restaurant_id=restaurant_id)

    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)

    date_filter = request.args.get('date')
    if date_filter:
        try:
            d = date.fromisoformat(date_filter)
            query = query.filter_by(shift_date=d)
        except ValueError:
            return jsonify({'error': 'Bad request', 'message': 'Invalid date format. Use YYYY-MM-DD'}), 400

    shifts = query.order_by(Shift.shift_date.desc(), Shift.start_time.desc()).all()

    return jsonify({'shifts': [s.to_dict() for s in shifts]}), 200


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
