"""Authentication endpoints - login, register, current user."""
import re

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt, verify_jwt_in_request

from app.extensions import db
from app.models.audit_log import AuditLog
from app.services.auth_service import AuthService

auth_bp = Blueprint('auth', __name__)
auth_bp.strict_slashes = False

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Bad request', 'message': 'Request body is required'}), 400

    # Restrict creation of admin/manager accounts: require a JWT from an admin user
    requested_role = data.get('role', 'viewer')
    if requested_role in ('admin', 'manager'):
        try:
            verify_jwt_in_request()
            claims = get_jwt()
            if claims.get('role') != 'admin':
                return jsonify({
                    'error': 'Forbidden',
                    'message': 'Only admins can create manager or admin accounts'
                }), 403
        except Exception:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Authentication required to create manager or admin accounts'
            }), 401

    result = AuthService.register_user(data)
    if 'error' in result:
        return jsonify({'error': result['error'], 'message': result['message']}), result['status_code']

    return jsonify(result), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Bad request', 'message': 'Email and password required'}), 400

    # Task 3: Email format validation
    if not EMAIL_REGEX.match(data['email']):
        return jsonify({'error': 'Invalid email format'}), 400

    result = AuthService.login_user(data['email'], data['password'])
    if 'error' in result:
        return jsonify({'error': result['error'], 'message': result['message']}), result['status_code']

    # Audit log: successful login
    user = result.get('user', {})
    audit_entry = AuditLog(
        user_id=user.get('user_id'),
        action='login',
        object_type='session',
        object_id=None,
        details='{"method": "password"}',
    )
    db.session.add(audit_entry)
    db.session.commit()

    return jsonify(result), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    user_id = get_jwt_identity()
    result = AuthService.get_current_user(user_id)
    if 'error' in result:
        return jsonify({'error': result['error'], 'message': result['message']}), result['status_code']

    return jsonify(result), 200
