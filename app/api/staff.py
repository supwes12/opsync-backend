"""Staff endpoints - list staff members with schedules and stats."""
from datetime import date, timedelta

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt

from app.models.staff_member import StaffMember
from app.models.staff_schedule import StaffSchedule

staff_bp = Blueprint('staff', __name__)
staff_bp.strict_slashes = False


def _get_current_week_range():
    """Return (monday, sunday) for the current week."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def _get_current_month_range():
    """Return (first_day, last_day) for the current month."""
    today = date.today()
    first_day = today.replace(day=1)
    # Last day: go to next month's first day and subtract 1
    if today.month == 12:
        last_day = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        last_day = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    return first_day, last_day


def _build_staff_response(member):
    """Build the full staff member response with schedule and stats."""
    monday, sunday = _get_current_week_range()
    month_start, month_end = _get_current_month_range()

    # Get current week schedule (Mon-Sun)
    week_schedules = (
        StaffSchedule.query
        .filter_by(staff_id=member.staff_id)
        .filter(StaffSchedule.date >= monday, StaffSchedule.date <= sunday)
        .order_by(StaffSchedule.date)
        .all()
    )

    # Get current month schedules for stats
    month_schedules = (
        StaffSchedule.query
        .filter_by(staff_id=member.staff_id)
        .filter(StaffSchedule.date >= month_start, StaffSchedule.date <= month_end)
        .all()
    )

    # Compute stats
    week_worked = [s for s in week_schedules if s.status in ('completed', 'scheduled')]
    month_worked = [s for s in month_schedules if s.status in ('completed', 'scheduled')]

    days_worked_week = len(week_worked)
    hours_week = sum(s.hours or 0 for s in week_worked)
    days_worked_month = len(month_worked)
    hours_month = sum(s.hours or 0 for s in month_worked)

    result = member.to_dict()
    result['schedule'] = [s.to_dict() for s in week_schedules]
    result['stats'] = {
        'days_worked_this_week': days_worked_week,
        'hours_this_week': hours_week,
        'days_worked_this_month': days_worked_month,
        'hours_this_month': hours_month,
    }
    return result


@staff_bp.route('/', methods=['GET'])
@jwt_required()
def list_staff():
    claims = get_jwt()
    restaurant_id = claims.get('restaurant_id')

    members = (
        StaffMember.query
        .filter_by(restaurant_id=restaurant_id)
        .order_by(StaffMember.last_name)
        .all()
    )

    return jsonify({
        'staff': [_build_staff_response(m) for m in members],
    }), 200


@staff_bp.route('/<staff_id>', methods=['GET'])
@jwt_required()
def get_staff_member(staff_id):
    from app.extensions import db
    member = db.session.get(StaffMember, staff_id)
    if not member:
        return jsonify({'error': 'Not found', 'message': 'Staff member not found'}), 404

    return jsonify({
        'staff_member': _build_staff_response(member),
    }), 200
