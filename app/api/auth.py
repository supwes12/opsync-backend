"""Authentication endpoints - login, register, current user."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.services.auth_service import AuthService

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Bad request', 'message': 'Request body is required'}), 400

    result = AuthService.register_user(data)
    if 'error' in result:
        return jsonify({'error': result['error'], 'message': result['message']}), result['status_code']

    return jsonify(result), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Bad request', 'message': 'Email and password required'}), 400

    result = AuthService.login_user(data['email'], data['password'])
    if 'error' in result:
        return jsonify({'error': result['error'], 'message': result['message']}), result['status_code']

    return jsonify(result), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    user_id = get_jwt_identity()
    result = AuthService.get_current_user(user_id)
    if 'error' in result:
        return jsonify({'error': result['error'], 'message': result['message']}), result['status_code']

    return jsonify(result), 200
