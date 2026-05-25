"""Alerts endpoints - list, acknowledge alerts."""
import json
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from sqlalchemy import case

from app.extensions import db
from app.models import Alert, Shift
from app.models.audit_log import AuditLog
from app.utils.decorators import role_required

alerts_bp = Blueprint('alerts', __name__)
alerts_bp.strict_slashes = False


@alerts_bp.route('/', methods=['GET'])
@jwt_required()
def list_alerts():
    claims = get_jwt()
    shift_id = request.args.get('shift_id')

    # Auto-detect shift_id from JWT restaurant_id if not provided
    if not shift_id:
        restaurant_id = request.args.get('restaurant_id', claims.get('restaurant_id'))
        if not restaurant_id:
            return jsonify({'error': 'Bad request', 'message': 'shift_id or restaurant_id is required'}), 400
        shift = Shift.query.filter_by(
            restaurant_id=restaurant_id, status='active'
        ).first()
        if not shift:
            return jsonify({'alerts': []}), 200
        shift_id = shift.shift_id

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


@alerts_bp.route('/<alert_id>/acknowledge', methods=['PUT', 'POST'])
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
    alert.acknowledged_at = datetime.now(timezone.utc)

    db.session.commit()

    # Audit log: alert acknowledged
    audit_entry = AuditLog(
        user_id=user_id,
        action='alert_acknowledged',
        object_type='alert',
        object_id=alert_id,
        details=json.dumps({
            'alert_type': alert.alert_type,
            'severity': alert.severity,
        }),
    )
    db.session.add(audit_entry)
    db.session.commit()

    return jsonify({'alert': alert.to_dict()}), 200
