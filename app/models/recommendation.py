"""Recommendation model - system-generated operational recommendations."""
from datetime import datetime, timezone

from app.extensions import db
from app.utils.helpers import generate_uuid


class Recommendation(db.Model):
    __tablename__ = 'recommendation'

    recommendation_id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    shift_id = db.Column(db.String(36), db.ForeignKey('shift.shift_id'), nullable=False)
    snapshot_id = db.Column(db.String(36), db.ForeignKey('operational_snapshot.snapshot_id'), nullable=False)
    rec_type = db.Column(db.String(30), nullable=False)
    priority = db.Column(db.String(10), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    rationale = db.Column(db.Text, nullable=False)
    suggested_action = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    actions = db.relationship('RecommendationAction', backref='recommendation', lazy='dynamic')

    def _compute_status(self):
        """Compute status from is_active and response actions."""
        # Check if there are any response actions
        latest_action = self.actions.order_by(
            db.text('responded_at DESC')
        ).first()

        if self.is_active:
            if latest_action and latest_action.response_type == 'accepted':
                return 'accepted'
            return 'pending'
        else:
            # Not active
            if latest_action:
                if latest_action.response_type == 'accepted':
                    return 'accepted'
                elif latest_action.response_type == 'deferred':
                    return 'deferred'
                elif latest_action.response_type == 'rejected':
                    return 'dismissed'
            return 'expired'

    def to_dict(self):
        return {
            'recommendation_id': self.recommendation_id,
            'shift_id': self.shift_id,
            'snapshot_id': self.snapshot_id,
            'type': self.rec_type,
            'priority': self.priority,
            'title': self.title,
            'description': self.description,
            'rationale': self.rationale,
            'suggested_action': self.suggested_action,
            'status': self._compute_status(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active,
        }

    def __repr__(self):
        return f'<Recommendation {self.rec_type}: {self.title}>'
