"""StaffSchedule model - daily schedule entries for staff members."""
from app.extensions import db
from app.utils.helpers import generate_uuid


class StaffSchedule(db.Model):
    __tablename__ = 'staff_schedule'

    schedule_id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    staff_id = db.Column(db.String(36), db.ForeignKey('staff_member.staff_id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    shift_type = db.Column(db.String(20), nullable=True)
    start_time = db.Column(db.String(5), nullable=True)
    end_time = db.Column(db.String(5), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='scheduled')
    hours = db.Column(db.Float, nullable=True)

    def to_dict(self):
        return {
            'schedule_id': self.schedule_id,
            'staff_id': self.staff_id,
            'date': self.date.isoformat() if self.date else None,
            'shift_type': self.shift_type,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'status': self.status,
            'hours': self.hours,
        }

    def __repr__(self):
        return f'<StaffSchedule {self.staff_id} on {self.date} ({self.status})>'
