"""Restaurant model - physical QSR locations."""
from datetime import datetime

from app.extensions import db
from app.utils.helpers import generate_uuid


class Restaurant(db.Model):
    __tablename__ = 'restaurant'

    restaurant_id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(2), nullable=False)
    zip_code = db.Column(db.String(10), nullable=False)
    format_type = db.Column(db.String(20), nullable=False)
    open_time = db.Column(db.Time, nullable=False)
    close_time = db.Column(db.Time, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    shifts = db.relationship('Shift', backref='restaurant', lazy='dynamic')
    users = db.relationship('User', backref='restaurant', lazy='dynamic')

    def to_dict(self):
        return {
            'restaurant_id': self.restaurant_id,
            'name': self.name,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'format_type': self.format_type,
            'open_time': self.open_time.isoformat() if self.open_time else None,
            'close_time': self.close_time.isoformat() if self.close_time else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<Restaurant {self.name} ({self.restaurant_id})>'
