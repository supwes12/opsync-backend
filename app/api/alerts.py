"""Alerts endpoints - list, acknowledge alerts."""
from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from sqlalchemy import case

from app.extensions import db
from app.models import Alert
from app.utils.decorators import role_required

alerts_bp = Blueprint('alerts', __name__)


@alerts_bp.route('/', methods=['GET'])
@jwt_required()
def list_alerts():
    shift_id = request.args.get('shift_id')
    if not shift_id:
        return jsonify({'error': 'Bad request', 'message': 'shift_id is required'}), 400

    query = Alert.query.filter_by(shift_id=shift_id)

    acknowledged = request.args.get('acknowledged')
    if acknowledged is not None:
        is_ack = acknowledged.lower() == 'true'
        query = query.filter_by(is_acknowledged=is_ack)

    severity = request.args.get('severity')
    if severity:
        query = query.filter_by(severity=severity)

    severity_order = case(
        (Alert.severity == 'critical', 1),
        (Alert.severity == 'warning', 2),
        (Alert.severity == 'info', 3),
        else_=4,
    )
    alerts = query.order_by(severity_order, Alert.created_at.desc()).all()

    return jsonify({'alerts': [a.to_dict() for a in alerts]}), 200


@alerts_bp.route('/<alert_id>/acknowledge', methods=['PUT'])
@role_required('admin', 'manager')
def acknowledge_alert(alert_id):
    alert = db.session.get(Alert, alert_id)
    if not alert:
        return jsonify({'error': 'Not found', 'message': 'Alert not found'}), 404

    if alert.is_acknowledged:
        return jsonify({'error': 'Bad request', 'message': 'Alert already acknowledged'}), 400

    user_id = get_jwt_identity()
    alert.is_acknowledged = True
    alert.acknowledged_by = user_id
    alert.acknowledged_at = datetime.utcnow()

    db.session.commit()

    return jsonify({'alert': alert.to_dict()}), 200
