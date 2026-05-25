"""Authentication service - handles registration, login, and user retrieval."""
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import User, Restaurant


class AuthService:
    @staticmethod
    def register_user(data):
        required = ['email', 'password', 'first_name', 'last_name', 'role', 'restaurant_id']
        for field in required:
            if not data.get(field):
                return {'error': 'Validation error', 'message': f'{field} is required', 'status_code': 400}

        if data['role'] not in ('admin', 'manager', 'viewer'):
            return {'error': 'Validation error', 'message': 'Role must be admin, manager, or viewer', 'status_code': 400}

        if User.query.filter_by(email=data['email']).first():
            return {'error': 'Conflict', 'message': 'Email already registered', 'status_code': 409}

        restaurant = db.session.get(Restaurant, data['restaurant_id'])
        if not restaurant:
            return {'error': 'Validation error', 'message': 'Restaurant not found', 'status_code': 400}

        user = User(
            email=data['email'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            role=data['role'],
            restaurant_id=data['restaurant_id'],
        )
        user.set_password(data['password'])

        db.session.add(user)
        db.session.commit()

        # Generate token with restaurant_id claim
        access_token = create_access_token(
            identity=user.user_id,
            additional_claims={
                'email': user.email,
                'role': user.role,
                'restaurant_id': user.restaurant_id,
            },
        )

        return {
            'message': 'User registered successfully',
            'user': user.to_dict(),
            'access_token': access_token,
        }

    @staticmethod
    def login_user(email, password):
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            return {'error': 'Unauthorized', 'message': 'Invalid email or password', 'status_code': 401}

        if not user.is_active:
            return {'error': 'Forbidden', 'message': 'Account is deactivated', 'status_code': 403}

        access_token = create_access_token(
            identity=user.user_id,
            additional_claims={
                'email': user.email,
                'role': user.role,
                'restaurant_id': user.restaurant_id,
            },
        )

        return {'access_token': access_token, 'user': user.to_dict()}

    @staticmethod
    def get_current_user(user_id):
        user = db.session.get(User, user_id)
        if not user:
            return {'error': 'Not found', 'message': 'User not found', 'status_code': 404}
        return {'user': user.to_dict()}
