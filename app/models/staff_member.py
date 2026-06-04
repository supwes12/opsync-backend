"""StaffMember model - restaurant employees."""
from datetime import datetime

from app.extensions import db
from app.utils.helpers import generate_uuid


class StaffMember(db.Model):
    __tablename__ = 'staff_member'

    staff_id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    restaurant_id = db.Column(db.String(36), db.ForeignKey('restaurant.restaurant_id'), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    position = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    hire_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='active')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    schedules = db.relationship('StaffSchedule', backref='staff_member', lazy='dynamic')

    def to_dict(self):
        return {
            'staff_id': self.staff_id,
            'restaurant_id': self.restaurant_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'position': self.position,
            'phone': self.phone,
            'email': self.email,
            'hire_date': self.hire_date.isoformat() if self.hire_date else None,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<StaffMember {self.first_name} {self.last_name} ({self.position})>'
