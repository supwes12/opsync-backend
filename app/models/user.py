"""User model - system users with roles (admin, manager, viewer)."""
from datetime import datetime, timezone

from app.extensions import db, bcrypt
from app.utils.helpers import generate_uuid


class User(db.Model):
    __tablename__ = 'users'

    user_id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    restaurant_id = db.Column(db.String(36), db.ForeignKey('restaurant.restaurant_id'), nullable=False)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    recommendation_actions = db.relationship('RecommendationAction', backref='user', lazy='dynamic')
    managed_shifts = db.relationship('Shift', backref='manager', lazy='dynamic', foreign_keys='Shift.manager_id')
    acknowledged_alerts = db.relationship('Alert', backref='acknowledger', lazy='dynamic', foreign_keys='Alert.acknowledged_by')

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def to_dict(self):
        restaurant_name = None
        if self.restaurant:
            restaurant_name = self.restaurant.name
        return {
            'user_id': self.user_id,
            'restaurant_id': self.restaurant_id,
            'restaurant_name': restaurant_name,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'
