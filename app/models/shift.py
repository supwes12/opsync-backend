"""Shift model - operating periods for restaurants."""
from app.extensions import db
from app.utils.helpers import generate_uuid


class Shift(db.Model):
    __tablename__ = 'shift'

    shift_id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    restaurant_id = db.Column(db.String(36), db.ForeignKey('restaurant.restaurant_id'), nullable=False)
    manager_id = db.Column(db.String(36), db.ForeignKey('users.user_id'), nullable=True)
    shift_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    shift_type = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='active')

    snapshots = db.relationship('OperationalSnapshot', backref='shift', lazy='dynamic')
    recommendations = db.relationship('Recommendation', backref='shift', lazy='dynamic')
    alerts = db.relationship('Alert', backref='shift', lazy='dynamic')

    def to_dict(self):
        manager_name = None
        if self.manager:
            manager_name = f'{self.manager.first_name} {self.manager.last_name}'
        return {
            'shift_id': self.shift_id,
            'restaurant_id': self.restaurant_id,
            'manager_id': self.manager_id,
            'manager_name': manager_name,
            'shift_date': self.shift_date.isoformat() if self.shift_date else None,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'shift_type': self.shift_type,
            'status': self.status,
        }

    def __repr__(self):
        return f'<Shift {self.shift_type} on {self.shift_date}>'
