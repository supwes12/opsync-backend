"""Alert model - threshold-triggered notifications."""
from datetime import datetime

from app.extensions import db
from app.utils.helpers import generate_uuid


class Alert(db.Model):
    __tablename__ = 'alert'

    alert_id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    shift_id = db.Column(db.String(36), db.ForeignKey('shift.shift_id'), nullable=False)
    snapshot_id = db.Column(db.String(36), db.ForeignKey('operational_snapshot.snapshot_id'), nullable=False)
    alert_type = db.Column(db.String(30), nullable=False)
    severity = db.Column(db.String(10), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_acknowledged = db.Column(db.Boolean, nullable=False, default=False)
    acknowledged_by = db.Column(db.String(36), db.ForeignKey('users.user_id'), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    acknowledged_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'alert_id': self.alert_id,
            'shift_id': self.shift_id,
            'snapshot_id': self.snapshot_id,
            'alert_type': self.alert_type,
            'severity': self.severity,
            'message': self.message,
            'is_acknowledged': self.is_acknowledged,
            'acknowledged_by': self.acknowledged_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
        }

    def __repr__(self):
        return f'<Alert {self.alert_type} ({self.severity})>'
