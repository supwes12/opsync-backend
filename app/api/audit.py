"""Audit trail endpoints - view recent audit logs."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt

from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.utils.decorators import role_required

audit_bp = Blueprint('audit', __name__)
audit_bp.strict_slashes = False


@audit_bp.route('/', methods=['GET'])
@role_required('admin', 'manager')
def list_audit_logs():
    claims = get_jwt()
    restaurant_id = claims.get('restaurant_id')

    limit = request.args.get('limit', 50, type=int)
    if limit <= 0:
        return jsonify({'audit_logs': []}), 200
    limit = min(limit, 500)  # Cap at 500

    # Join with User to filter by restaurant_id
    logs = (
        db.session.query(AuditLog)
        .join(User, AuditLog.user_id == User.user_id)
        .filter(User.restaurant_id == restaurant_id)
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
        .all()
    )

    return jsonify({'audit_logs': [log.to_dict() for log in logs]}), 200
