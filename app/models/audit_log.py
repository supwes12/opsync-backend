"""AuditLog model - tracks user actions for audit trail."""
import json
from datetime import datetime

from app.extensions import db
from app.utils.helpers import generate_uuid


class AuditLog(db.Model):
    __tablename__ = 'audit_log'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.user_id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    object_type = db.Column(db.String(50), nullable=False)
    object_id = db.Column(db.String(36), nullable=True)
    details = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.now)

    user = db.relationship('User', backref=db.backref('audit_logs', lazy='dynamic'))

    def to_dict(self):
        user_email = None
        user_name = None
        if self.user:
            user_email = self.user.email
            user_name = f'{self.user.first_name} {self.user.last_name}'

        parsed_details = None
        if self.details:
            try:
                parsed_details = json.loads(self.details)
            except (json.JSONDecodeError, TypeError):
                parsed_details = self.details

        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_email': user_email,
            'user_name': user_name,
            'action': self.action,
            'object_type': self.object_type,
            'object_id': self.object_id,
            'details': parsed_details,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
        }

    def __repr__(self):
        return f'<AuditLog {self.action} by {self.user_id}>'
