"""Alert model - threshold-triggered notifications."""
import re
from datetime import datetime, timezone

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
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    acknowledged_at = db.Column(db.DateTime, nullable=True)

    def _compute_title(self):
        """Generate a human-friendly title from alert_type and severity."""
        type_titles = {
            'ticket_time_critical': 'High Ticket Time',
            'ticket_time_warning': 'High Ticket Time',
            'queue_surge': 'Queue Surge Detected',
            'stockout_risk': 'Inventory Stockout Risk',
            'labor_imbalance': 'Labor Imbalance',
            'labor_overstaffed_front': 'Front Counter Overstaffed',
            'demand_surge': 'Demand Surge Detected',
        }
        title_body = type_titles.get(self.alert_type)
        if not title_body:
            # Fallback: humanize the alert_type
            title_body = self.alert_type.replace('_', ' ').title()

        severity_prefix = (self.severity or 'info').capitalize()
        return f'{severity_prefix}: {title_body}'

    def _extract_threshold_value(self):
        """Try to extract threshold value from message text."""
        # Look for patterns like "exceeding the 180s warning threshold" or "300s threshold"
        match = re.search(r'(\d+)s\s+(?:warning\s+)?threshold', self.message or '')
        if match:
            return float(match.group(1))
        # Look for patterns like "threshold: 10" or "threshold: 10:1"
        match = re.search(r'threshold:\s*([\d.]+)', self.message or '')
        if match:
            return float(match.group(1))
        # Look for patterns like "150% threshold breached"
        match = re.search(r'(\d+)%\s+threshold', self.message or '')
        if match:
            return float(match.group(1))
        # For stockout alerts, the threshold is 20% par level
        if 'par level' in (self.message or ''):
            return 20.0
        return 0

    def _extract_actual_value(self):
        """Try to extract actual/current value from message text."""
        # Look for patterns like "Current avg ticket time: 310s"
        match = re.search(r'[Cc]urrent\s+(?:avg\s+)?(?:ticket\s+time|average)[:\s]+(\d+)s', self.message or '')
        if match:
            return float(match.group(1))
        # Look for patterns like "ticket time is 200s"
        match = re.search(r'ticket time is (\d+)s', self.message or '')
        if match:
            return float(match.group(1))
        # Look for patterns like "ratio: 12.5:1"
        match = re.search(r'ratio:\s*([\d.]+)', self.message or '')
        if match:
            return float(match.group(1))
        # Look for percentage patterns like "150% above" or "165% above"
        match = re.search(r'(\d+)%\s+above', self.message or '')
        if match:
            return float(match.group(1))
        # Look for patterns like "at 15% of daily par level"
        match = re.search(r'at\s+(\d+)%\s+of\s+(?:daily\s+)?par', self.message or '')
        if match:
            return float(match.group(1))
        return 0

    def to_dict(self):
        return {
            'alert_id': self.alert_id,
            'shift_id': self.shift_id,
            'snapshot_id': self.snapshot_id,
            'type': self.alert_type,
            'severity': self.severity,
            'title': self._compute_title(),
            'message': self.message,
            'threshold_value': self._extract_threshold_value(),
            'actual_value': self._extract_actual_value(),
            'acknowledged': self.is_acknowledged,
            'acknowledged_by': self.acknowledged_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
        }

    def __repr__(self):
        return f'<Alert {self.alert_type} ({self.severity})>'
