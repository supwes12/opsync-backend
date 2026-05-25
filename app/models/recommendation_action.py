"""RecommendationAction model - manager responses to recommendations."""
from datetime import datetime, timezone

from app.extensions import db
from app.utils.helpers import generate_uuid


class RecommendationAction(db.Model):
    __tablename__ = 'recommendation_action'

    action_id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    recommendation_id = db.Column(db.String(36), db.ForeignKey('recommendation.recommendation_id'), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('users.user_id'), nullable=False)
    response_type = db.Column(db.String(20), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    responded_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        user_name = None
        if self.user:
            user_name = f'{self.user.first_name} {self.user.last_name}'
        return {
            'action_id': self.action_id,
            'recommendation_id': self.recommendation_id,
            'user_id': self.user_id,
            'user_name': user_name,
            'response_type': self.response_type,
            'notes': self.notes,
            'responded_at': self.responded_at.isoformat() if self.responded_at else None,
        }

    def __repr__(self):
        return f'<Action {self.response_type} by {self.user_id}>'
