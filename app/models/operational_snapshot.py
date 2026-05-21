"""OperationalSnapshot model - time-series metrics captured every 30-60s."""
import json

from app.extensions import db
from app.utils.helpers import generate_uuid


class OperationalSnapshot(db.Model):
    __tablename__ = 'operational_snapshot'

    snapshot_id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    shift_id = db.Column(db.String(36), db.ForeignKey('shift.shift_id'), nullable=False)
    captured_at = db.Column(db.DateTime, nullable=False)
    total_orders = db.Column(db.Integer, nullable=False)
    dine_in_orders = db.Column(db.Integer, nullable=True)
    drive_thru_orders = db.Column(db.Integer, nullable=True)
    pickup_orders = db.Column(db.Integer, nullable=True)
    delivery_orders = db.Column(db.Integer, nullable=True)
    avg_ticket_time_sec = db.Column(db.Integer, nullable=True)
    staff_count = db.Column(db.Integer, nullable=False)
    kitchen_staff = db.Column(db.Integer, nullable=True)
    front_staff = db.Column(db.Integer, nullable=True)
    inventory_json = db.Column(db.Text, nullable=True)

    recommendations = db.relationship('Recommendation', backref='snapshot', lazy='dynamic')
    alerts = db.relationship('Alert', backref='snapshot', lazy='dynamic')

    @property
    def inventory(self):
        if self.inventory_json:
            return json.loads(self.inventory_json)
        return None

    @inventory.setter
    def inventory(self, value):
        if value is not None:
            self.inventory_json = json.dumps(value)
        else:
            self.inventory_json = None

    def to_dict(self):
        return {
            'snapshot_id': self.snapshot_id,
            'shift_id': self.shift_id,
            'captured_at': self.captured_at.isoformat() if self.captured_at else None,
            'total_orders': self.total_orders,
            'dine_in_orders': self.dine_in_orders,
            'drive_thru_orders': self.drive_thru_orders,
            'pickup_orders': self.pickup_orders,
            'delivery_orders': self.delivery_orders,
            'avg_ticket_time_sec': self.avg_ticket_time_sec,
            'staff_count': self.staff_count,
            'kitchen_staff': self.kitchen_staff,
            'front_staff': self.front_staff,
            'inventory': self.inventory,
        }

    def __repr__(self):
        return f'<Snapshot {self.snapshot_id} at {self.captured_at}>'
