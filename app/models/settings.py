"""Settings model - configurable thresholds per restaurant."""
from datetime import datetime

from app.extensions import db
from app.utils.helpers import generate_uuid


class Settings(db.Model):
    __tablename__ = 'settings'

    settings_id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    restaurant_id = db.Column(
        db.String(36),
        db.ForeignKey('restaurant.restaurant_id'),
        nullable=False,
        unique=True,
    )
    queue_surge = db.Column(db.Float, nullable=False, default=1.50)
    low_inventory = db.Column(db.Float, nullable=False, default=0.20)
    labor_imbalance = db.Column(db.Float, nullable=False, default=10.0)
    ticket_time_max = db.Column(db.Integer, nullable=False, default=300)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    restaurant = db.relationship('Restaurant', backref=db.backref('settings', uselist=False))

    def to_dict(self):
        return {
            'settings_id': self.settings_id,
            'restaurant_id': self.restaurant_id,
            'queue_surge': self.queue_surge,
            'low_inventory': self.low_inventory,
            'labor_imbalance': self.labor_imbalance,
            'ticket_time_max': self.ticket_time_max,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<Settings for restaurant {self.restaurant_id}>'
