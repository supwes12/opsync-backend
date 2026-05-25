"""Settings endpoints - threshold configuration per restaurant."""
import json

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity

from app.extensions import db
from app.models.settings import Settings
from app.models.audit_log import AuditLog
from app.utils.decorators import role_required

settings_bp = Blueprint('settings', __name__)
settings_bp.strict_slashes = False


@settings_bp.route('/', methods=['GET'])
@jwt_required()
def get_settings():
    claims = get_jwt()
    restaurant_id = request.args.get('restaurant_id', claims.get('restaurant_id'))

    if not restaurant_id:
        return jsonify({'error': 'Bad request', 'message': 'restaurant_id is required'}), 400

    settings = Settings.query.filter_by(restaurant_id=restaurant_id).first()
    if not settings:
        # Return defaults if no settings exist yet
        settings = Settings(restaurant_id=restaurant_id)
        db.session.add(settings)
        db.session.commit()

    return jsonify(settings.to_dict()), 200


@settings_bp.route('/', methods=['PUT'])
@role_required('admin', 'manager')
def update_settings():
    claims = get_jwt()
    restaurant_id = claims.get('restaurant_id')

    if not restaurant_id:
        return jsonify({'error': 'Bad request', 'message': 'restaurant_id is required'}), 400

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Bad request', 'message': 'Request body is required'}), 400

    settings = Settings.query.filter_by(restaurant_id=restaurant_id).first()
    if not settings:
        settings = Settings(restaurant_id=restaurant_id)
        db.session.add(settings)

    if 'queue_surge' in data:
        settings.queue_surge = float(data['queue_surge'])
    if 'low_inventory' in data:
        settings.low_inventory = float(data['low_inventory'])
    if 'labor_imbalance' in data:
        settings.labor_imbalance = float(data['labor_imbalance'])
    if 'ticket_time_max' in data:
        settings.ticket_time_max = int(data['ticket_time_max'])

    db.session.commit()

    # Audit log: settings updated
    user_id = get_jwt_identity()
    audit_entry = AuditLog(
        user_id=user_id,
        action='settings_updated',
        object_type='settings',
        object_id=restaurant_id,
        details=json.dumps(data),
    )
    db.session.add(audit_entry)
    db.session.commit()

    return jsonify(settings.to_dict()), 200
