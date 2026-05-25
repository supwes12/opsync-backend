"""Restaurants endpoints - CRUD (admin only)."""
from datetime import time

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt

from app.extensions import db
from app.models import Restaurant
from app.utils.decorators import role_required

restaurants_bp = Blueprint('restaurants', __name__)
restaurants_bp.strict_slashes = False


@restaurants_bp.route('/', methods=['GET'])
@role_required('admin')
def list_restaurants():
    restaurants = Restaurant.query.all()
    return jsonify({'restaurants': [r.to_dict() for r in restaurants]}), 200


@restaurants_bp.route('/<restaurant_id>', methods=['GET'])
@jwt_required()
def get_restaurant(restaurant_id):
    claims = get_jwt()
    if claims.get('role') != 'admin' and claims.get('restaurant_id') != restaurant_id:
        return jsonify({'error': 'Forbidden', 'message': 'Access denied'}), 403

    restaurant = db.session.get(Restaurant, restaurant_id)
    if not restaurant:
        return jsonify({'error': 'Not found', 'message': 'Restaurant not found'}), 404

    return jsonify({'restaurant': restaurant.to_dict()}), 200


@restaurants_bp.route('/', methods=['POST'])
@role_required('admin')
def create_restaurant():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Bad request', 'message': 'Request body is required'}), 400

    required = ['name', 'address', 'city', 'state', 'zip_code', 'format_type', 'open_time', 'close_time']
    for field in required:
        if not data.get(field):
            return jsonify({'error': 'Validation error', 'message': f'{field} is required'}), 400

    try:
        open_time = time.fromisoformat(data['open_time'])
        close_time = time.fromisoformat(data['close_time'])
    except (ValueError, TypeError):
        return jsonify({'error': 'Validation error', 'message': 'open_time and close_time must be valid time strings (HH:MM)'}), 400

    restaurant = Restaurant(
        name=data['name'],
        address=data['address'],
        city=data['city'],
        state=data['state'],
        zip_code=data['zip_code'],
        format_type=data['format_type'],
        open_time=open_time,
        close_time=close_time,
    )

    db.session.add(restaurant)
    db.session.commit()

    return jsonify({'restaurant': restaurant.to_dict()}), 201


@restaurants_bp.route('/<restaurant_id>', methods=['PUT'])
@role_required('admin')
def update_restaurant(restaurant_id):
    restaurant = db.session.get(Restaurant, restaurant_id)
    if not restaurant:
        return jsonify({'error': 'Not found', 'message': 'Restaurant not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Bad request', 'message': 'Request body is required'}), 400

    updatable = ['name', 'address', 'city', 'state', 'zip_code', 'format_type']
    for field in updatable:
        if field in data:
            setattr(restaurant, field, data[field])

    if 'open_time' in data:
        try:
            restaurant.open_time = time.fromisoformat(data['open_time'])
        except (ValueError, TypeError):
            return jsonify({'error': 'Validation error', 'message': 'Invalid open_time format'}), 400

    if 'close_time' in data:
        try:
            restaurant.close_time = time.fromisoformat(data['close_time'])
        except (ValueError, TypeError):
            return jsonify({'error': 'Validation error', 'message': 'Invalid close_time format'}), 400

    db.session.commit()

    return jsonify({'restaurant': restaurant.to_dict()}), 200


@restaurants_bp.route('/<restaurant_id>', methods=['DELETE'])
@role_required('admin')
def delete_restaurant(restaurant_id):
    restaurant = db.session.get(Restaurant, restaurant_id)
    if not restaurant:
        return jsonify({'error': 'Not found', 'message': 'Restaurant not found'}), 404

    db.session.delete(restaurant)
    db.session.commit()

    return jsonify({'message': 'Restaurant deleted'}), 200
