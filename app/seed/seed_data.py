"""Database seeding script with realistic restaurant operational data."""

import json
import random
from datetime import datetime, date, time, timedelta

from app import create_app
from app.extensions import db
from app.models import (
    Restaurant, User, Shift, OperationalSnapshot,
    Recommendation, RecommendationAction, Alert, Settings,
    StaffMember, StaffSchedule,
)

random.seed(42)


def clear_all_data():
    """Drop all data in reverse dependency order."""
    from app.models.audit_log import AuditLog
    AuditLog.query.delete()
    RecommendationAction.query.delete()
    Alert.query.delete()
    Recommendation.query.delete()
    OperationalSnapshot.query.delete()
    Shift.query.delete()
    StaffSchedule.query.delete()
    StaffMember.query.delete()
    Settings.query.delete()
    User.query.delete()
    Restaurant.query.delete()
    db.session.commit()
    print("  Cleared all existing data.")


def seed_restaurants():
    """Create 3 restaurant locations."""
    restaurants = [
        Restaurant(
            name='OpSync Burger - Downtown',
            address='1200 Main St',
            city='Dallas',
            state='TX',
            zip_code='75201',
            format_type='drive_thru',
            open_time=time(6, 0),
            close_time=time(23, 0),
        ),
        Restaurant(
            name='OpSync Burger - Suburban',
            address='4500 Legacy Dr',
            city='Plano',
            state='TX',
            zip_code='75024',
            format_type='combo',
            open_time=time(7, 0),
            close_time=time(22, 0),
        ),
        Restaurant(
            name='OpSync Burger - Airport',
            address='2333 S Service Rd',
            city='Irving',
            state='TX',
            zip_code='75062',
            format_type='dine_in',
            open_time=time(5, 0),
            close_time=time(0, 0),
        ),
    ]
    for r in restaurants:
        db.session.add(r)
    db.session.commit()
    return restaurants


def seed_users(restaurants):
    """Create 3 users per restaurant (admin, manager, viewer)."""
    city_key = {'Dallas': 'dallas', 'Plano': 'plano', 'Irving': 'irving'}
    names = {
        'dallas': [
            ('James', 'Henderson', 'admin'),
            ('Maria', 'Gonzalez', 'manager'),
            ('Tyler', 'Brooks', 'viewer'),
        ],
        'plano': [
            ('Sarah', 'Mitchell', 'admin'),
            ('David', 'Chen', 'manager'),
            ('Ashley', 'Patel', 'viewer'),
        ],
        'irving': [
            ('Robert', 'Kim', 'admin'),
            ('Jessica', 'Thompson', 'manager'),
            ('Brandon', 'Rivera', 'viewer'),
        ],
    }
    passwords = {'admin': 'admin123', 'manager': 'manager123', 'viewer': 'viewer123'}

    users_map = {}
    for restaurant in restaurants:
        key = city_key[restaurant.city]
        user_list = []
        for first, last, role in names[key]:
            email = f'{role}@{key}.opsync.com'
            user = User(
                restaurant_id=restaurant.restaurant_id,
                email=email,
                first_name=first,
                last_name=last,
                role=role,
                is_active=True,
            )
            user.set_password(passwords[role])
            db.session.add(user)
            user_list.append(user)
        users_map[restaurant.restaurant_id] = user_list
    db.session.commit()
    return users_map


def seed_shifts(restaurants, users_map):
    """Create shifts spanning 14 days for all restaurants.

    Today's shifts get 'active' status; historical shifts are 'completed'.
    """
    today = date.today()
    shifts = []
    shifts_by_day = {}  # {(restaurant_id, date): [shifts]}

    for restaurant in restaurants:
        restaurant_users = users_map[restaurant.restaurant_id]
        manager = next(u for u in restaurant_users if u.role == 'manager')

        for day_offset in range(13, -1, -1):
            day = today - timedelta(days=day_offset)
            is_today = (day == today)

            if restaurant.city == 'Dallas':
                shift_defs = [
                    ('morning', 6, 0, 12, 0),
                    ('lunch', 11, 0, 17, 0),
                    ('dinner', 16, 0, 23, 0),
                ]
            elif restaurant.city == 'Plano':
                shift_defs = [
                    ('morning', 7, 0, 13, 0),
                    ('lunch', 12, 0, 18, 0),
                ]
            else:
                shift_defs = [
                    ('morning', 5, 0, 11, 0),
                    ('lunch', 10, 0, 16, 0),
                ]

            day_key = (restaurant.restaurant_id, day)
            shifts_by_day[day_key] = []

            for i, (shift_type, sh, sm, eh, em) in enumerate(shift_defs):
                if is_today:
                    # Today: first shift completed, rest active
                    status = 'completed' if i == 0 else 'active'
                else:
                    status = 'completed'

                shift = Shift(
                    restaurant_id=restaurant.restaurant_id,
                    manager_id=manager.user_id,
                    shift_date=day,
                    start_time=datetime(day.year, day.month, day.day, sh, sm),
                    end_time=datetime(day.year, day.month, day.day, eh, em),
                    shift_type=shift_type,
                    status=status,
                )
                db.session.add(shift)
                shifts.append(shift)
                shifts_by_day[day_key].append(shift)

    db.session.commit()
    return shifts, shifts_by_day


def _make_inventory(phase, minutes_in):
    """Generate inventory dict that degrades realistically during service."""
    base = {
        'chicken_breast': {'par': 100, 'unit': 'pieces'},
        'french_fries': {'par': 80, 'unit': 'lbs'},
        'burger_patties': {'par': 120, 'unit': 'pieces'},
        'lettuce': {'par': 30, 'unit': 'heads'},
        'tomatoes': {'par': 40, 'unit': 'lbs'},
        'soda_syrup': {'par': 6, 'unit': 'boxes'},
        'cups_large': {'par': 500, 'unit': 'count'},
        'napkins': {'par': 1000, 'unit': 'count'},
    }

    if phase == 'ramp':
        pct = max(0.55 - minutes_in * 0.005, 0.40)
    elif phase == 'peak':
        pct = max(0.40 - minutes_in * 0.008, 0.12)
    else:
        pct = max(0.25 - minutes_in * 0.002, 0.18)

    inv = {}
    for item, info in base.items():
        noise = random.uniform(0.85, 1.15)
        current = max(1, int(info['par'] * pct * noise))
        inv[item] = {'current': current, 'par': info['par'], 'unit': info['unit']}
    return inv


def _generate_snapshot_for_hour(shift, hour, day_factor=1.0):
    """Generate a single snapshot for a given hour within a shift.

    day_factor adds day-to-day variation (0.8 - 1.2 range).
    Returns the snapshot object (not yet committed).
    """
    day = shift.shift_date
    t = datetime(day.year, day.month, day.day, hour, random.randint(0, 15))

    # Realistic order patterns by hour of day
    # Morning ramp 6-10, lunch peak 11-13, afternoon 14-16, dinner 17-20, late 21-23
    hour_profiles = {
        5: 3, 6: 5, 7: 10, 8: 15, 9: 18,
        10: 22, 11: 35, 12: 50, 13: 45,
        14: 28, 15: 20, 16: 22, 17: 30,
        18: 38, 19: 35, 20: 28, 21: 18, 22: 10,
    }
    base_orders = hour_profiles.get(hour, 10)
    total = max(2, int(base_orders * day_factor + random.randint(-2, 2)))

    # Channel distribution
    dr = max(0, int(total * 0.35) + random.randint(-2, 2))
    dt = max(0, int(total * 0.25) + random.randint(-1, 1))
    pk = max(0, int(total * 0.20) + random.randint(-1, 1))
    dl = max(0, total - dr - dt - pk)

    # Ticket time varies by load
    if total > 40:
        base_ticket = 160 + random.randint(-15, 30)
    elif total > 25:
        base_ticket = 120 + random.randint(-10, 20)
    else:
        base_ticket = 85 + random.randint(-10, 15)
    ticket = max(60, int(base_ticket * day_factor))

    # Staff levels vary by time of day
    if 11 <= hour <= 14 or 17 <= hour <= 20:
        staff, kitchen, front = 7, 4, 3
    elif 7 <= hour <= 10 or 15 <= hour <= 16:
        staff, kitchen, front = 5, 2, 3
    else:
        staff, kitchen, front = 4, 2, 2

    # Determine phase for inventory
    if hour < 11:
        phase = 'ramp'
        phase_min = (hour - 6) * 60
    elif hour < 14:
        phase = 'peak'
        phase_min = (hour - 11) * 60
    else:
        phase = 'cool'
        phase_min = (hour - 14) * 60

    snap = OperationalSnapshot(
        shift_id=shift.shift_id,
        captured_at=t,
        total_orders=total,
        dine_in_orders=dt,
        drive_thru_orders=dr,
        pickup_orders=pk,
        delivery_orders=dl,
        avg_ticket_time_sec=ticket,
        staff_count=staff,
        kitchen_staff=kitchen,
        front_staff=front,
    )
    snap.inventory = _make_inventory(phase, phase_min)
    return snap


def seed_snapshots(shifts):
    """Create operational snapshots spanning 14 days.

    Generates ~10 snapshots per shift (one per hour during business hours).
    Today's Downtown lunch shift gets detailed 5-minute snapshots for live demo.
    """
    snapshots = []
    today = date.today()
    today_lunch_snapshots = []

    # Group shifts for processing
    today_downtown_lunch = None

    for shift in shifts:
        is_today = shift.shift_date == today
        is_downtown = shift.restaurant and shift.restaurant.city == 'Dallas'

        day_offset = (today - shift.shift_date).days
        weekday = shift.shift_date.weekday()
        if weekday in (5, 6):  # weekend — slightly busier
            day_factor = 1.10 + (weekday - 5) * 0.05
        else:
            day_factor = 0.95 + weekday * 0.02

        start_hour = shift.start_time.hour
        end_hour = shift.end_time.hour
        if end_hour <= start_hour:
            end_hour = 23

        # Today's Downtown lunch shift: detailed 5-minute snapshots
        # Simulates that it's currently ~12:30 PM during peak lunch rush.
        # 19 snapshots from 11:00 to 12:30 — ramp then peak.
        # The latest snapshot should show a busy restaurant.
        if is_today and is_downtown and shift.shift_type == 'lunch':
            today_downtown_lunch = shift
            # 7 snapshots: 11:00 through 12:30 (15-min intervals)
            for i in range(7):
                t = datetime(today.year, today.month, today.day, 11, 0) + timedelta(minutes=i * 15)
                minutes_in = i * 15

                if minutes_in < 60:
                    phase = 'ramp'
                    base_orders = 18 + int(20 * (minutes_in / 60))
                    base_ticket = 90 + int(60 * (minutes_in / 60))
                    staff, kitchen, front = 7, 4, 3
                else:
                    phase = 'peak'
                    peak_min = minutes_in - 60
                    base_orders = 38 + int(10 * (peak_min / 60))
                    base_ticket = 155 + int(40 * (peak_min / 60))
                    staff, kitchen, front = 8, 4, 4

                total = max(2, base_orders + random.randint(-2, 2))
                # Channel split: drive-thru 40%, delivery 25%, dine-in 20%, pickup 15%
                dr = max(0, int(total * 0.40) + random.randint(-2, 2))
                dl = max(0, int(total * 0.25) + random.randint(-1, 2))
                dt = max(0, int(total * 0.20) + random.randint(-1, 1))
                pk = max(0, total - dr - dl - dt)
                ticket = max(60, base_ticket + random.randint(-12, 12))

                # Make queue_depth realistic for the snapshot model
                # (queue_depth is computed as total_orders / staff in to_dict)

                snap = OperationalSnapshot(
                    shift_id=shift.shift_id,
                    captured_at=t,
                    total_orders=total,
                    dine_in_orders=dt,
                    drive_thru_orders=dr,
                    pickup_orders=pk,
                    delivery_orders=dl,
                    avg_ticket_time_sec=ticket,
                    staff_count=staff,
                    kitchen_staff=kitchen,
                    front_staff=front,
                )
                snap.inventory = _make_inventory(
                    phase,
                    minutes_in if phase == 'ramp' else minutes_in - 60,
                )
                db.session.add(snap)
                snapshots.append(snap)
                today_lunch_snapshots.append(snap)
            continue

        # All other shifts: ~1 snapshot per hour
        for hour in range(start_hour, end_hour):
            snap = _generate_snapshot_for_hour(shift, hour, day_factor)
            db.session.add(snap)
            snapshots.append(snap)

    db.session.commit()
    return snapshots, today_lunch_snapshots


def seed_recommendations(shifts, lunch_snapshots):
    """Create recommendations.

    Today's Downtown lunch gets 10 detailed recommendations.
    Historical days get 2-4 recommendations each for the Downtown restaurant.
    """
    today = date.today()
    recommendations = []

    # --- Today's Downtown lunch: detailed recommendations (same as before) ---
    downtown_lunch = None
    for s in shifts:
        if s.shift_type == 'lunch' and s.restaurant.city == 'Dallas' and s.shift_date == today:
            downtown_lunch = s
            break

    if downtown_lunch and lunch_snapshots:
        peak_snaps = [s for s in lunch_snapshots if s.avg_ticket_time_sec >= 150]
        ramp_snaps = [s for s in lunch_snapshots if s.avg_ticket_time_sec < 150]

        # Helper to safely pick a snapshot by index with fallback
        def _pick(lst, idx, fallback_lst, fallback_idx):
            if len(lst) > idx:
                return lst[idx]
            return fallback_lst[min(fallback_idx, len(fallback_lst) - 1)]

        rec_defs = [
            # --- HIGH PRIORITY (active - need manager attention) ---
            {
                'snap': _pick(peak_snaps, 0, lunch_snapshots, 12),
                'rec_type': 'labor',
                'priority': 'high',
                'title': 'Reallocate 1 front counter staff to drive-thru',
                'description': (
                    'Drive-thru is currently bottlenecked with 16 vehicles in queue and average wait times exceeding 6 minutes. '
                    'Front counter has 3 staff serving only 4 dine-in customers. Moving one front staff to drive-thru expediting '
                    'will reduce queue wait by an estimated 35% based on historical throughput data.'
                ),
                'rationale': (
                    f'Drive-thru accounts for 40% of current revenue but ticket time has reached '
                    f'{peak_snaps[0].avg_ticket_time_sec if peak_snaps else 180}s. '
                    f'Front counter utilization is at 22% while drive-thru is at 94%. '
                    f'Rebalancing will normalize throughput across channels.'
                ),
                'suggested_action': 'Move one front counter team member to drive-thru window #2 for order handoff and bagging.',
                'is_active': True,
            },
            {
                'snap': _pick(peak_snaps, 3, lunch_snapshots, 16),
                'rec_type': 'inventory',
                'priority': 'high',
                'title': 'Begin emergency chicken prep — projected stockout in 45 min',
                'description': (
                    'Chicken breast inventory has dropped to 14 pieces against a par of 100. '
                    'At the current consumption rate of 2.1 pieces per minute, complete stockout is projected in approximately 7 minutes. '
                    'Chicken items represent 28% of current orders. A stockout will force menu modifications and damage customer satisfaction.'
                ),
                'rationale': (
                    'Chicken breast: 14 remaining / 100 par (14%). Consumption rate: 2.1/min during peak. '
                    'Freezer backup has ~40 pieces requiring 12-min thaw cycle. '
                    'Supplier emergency delivery ETA is 35 minutes if called now.'
                ),
                'suggested_action': 'Immediately pull chicken from freezer backup and begin thaw. Simultaneously place emergency call to distributor for same-day delivery.',
                'is_active': True,
            },
            {
                'snap': _pick(peak_snaps, 4, lunch_snapshots, 17),
                'rec_type': 'operations',
                'priority': 'high',
                'title': 'Open second drive-thru window to reduce queue',
                'description': (
                    'Drive-thru queue has reached 16 vehicles with average service time of 312 seconds per vehicle. '
                    'Opening the second window for order handoff will split the bottleneck and reduce effective wait time by 40-50%.'
                ),
                'rationale': (
                    'Current single-window throughput: ~12 vehicles/hr. Dual-window capacity: ~20 vehicles/hr. '
                    'Queue depth of 16 means last car waits ~80 minutes at current rate. '
                    'Industry benchmark for acceptable drive-thru wait: under 4 minutes.'
                ),
                'suggested_action': 'Activate Window #2 — assign one staff to payment/handoff while primary window handles order-taking.',
                'is_active': True,
            },
            # --- MEDIUM PRIORITY ---
            {
                'snap': _pick(peak_snaps, 2, lunch_snapshots, 15),
                'rec_type': 'labor',
                'priority': 'medium',
                'title': 'Consider calling in additional kitchen staff for dinner rush',
                'description': (
                    'Current kitchen team of 4 is strained at 94% utilization during lunch. '
                    'Dinner rush historically brings 15-20% higher volume on this day of the week. '
                    'Calling in one additional kitchen staff member now gives 90 minutes lead time for shift prep.'
                ),
                'rationale': (
                    'Kitchen utilization at 94% during lunch with ticket times at 200s+. '
                    'Historical data shows this weekday dinner peaks at 55-60 orders/hr. '
                    'Current 4-person kitchen team cannot sustain that volume without degradation.'
                ),
                'suggested_action': 'Call in one off-duty kitchen team member (Tyler or Sarah) for a 4:00 PM - 10:00 PM shift.',
                'is_active': True,
            },
            {
                'snap': _pick(peak_snaps, 1, lunch_snapshots, 14),
                'rec_type': 'operations',
                'priority': 'medium',
                'title': 'Reduce drive-thru menu options to speed throughput',
                'description': (
                    'During extreme queue conditions, temporarily limiting drive-thru to top 8 menu items '
                    'can reduce average prep time by 25%. This is a standard QSR surge protocol used by major chains.'
                ),
                'rationale': (
                    'Top 8 items account for 72% of drive-thru orders. Complex specialty items add 45-90 seconds to prep time. '
                    'Temporary simplification during peak reduces kitchen cognitive load and speeds assembly line.'
                ),
                'suggested_action': 'Post "Express Menu" signage at drive-thru order board. Limit to: Classic Burger, Cheeseburger, Chicken Sandwich, Nuggets (6/10), Fries (S/M/L), Drinks, Shakes.',
                'is_active': True,
            },
            {
                'snap': _pick(peak_snaps, 5, lunch_snapshots, 18),
                'rec_type': 'prep',
                'priority': 'medium',
                'title': 'Begin dinner prep during any staffing slack',
                'description': (
                    'Dinner shift starts at 16:00. Key dinner items need marination (45 min), '
                    'portioning (30 min), and staging. If any staff become available during the '
                    'current rush, redirect them to prep work.'
                ),
                'rationale': (
                    'Dinner shift starts in ~3.5 hours. Chicken marination requires 45 min. '
                    'Burger patty portioning takes 30 min. Starting when possible ensures readiness.'
                ),
                'suggested_action': 'When drive-thru queue drops below 10, assign 1 kitchen staff to dinner prep: marinate 60 chicken breasts, portion 80 burger patties.',
                'is_active': False,
            },
            # --- LOW PRIORITY ---
            {
                'snap': _pick(ramp_snaps, -1, lunch_snapshots, 10),
                'rec_type': 'prep',
                'priority': 'low',
                'title': 'Pre-stage delivery packaging for anticipated pickup surge',
                'description': (
                    'Delivery orders are running 20% above forecast. Based on historical patterns, '
                    'a secondary delivery surge is expected between 5:00-6:30 PM. '
                    'Pre-staging bags, napkins, and utensil packs now prevents scrambling during dinner.'
                ),
                'rationale': (
                    'Current delivery volume: 12 orders/hr (forecast was 10). '
                    'Historical Thursday dinner delivery peaks at 18-22 orders/hr. '
                    'Each delivery order requires bag assembly averaging 45 seconds.'
                ),
                'suggested_action': 'Pre-assemble 50 delivery bags with napkins, utensils, and condiment packs. Stage near expo station.',
                'is_active': False,
            },
            {
                'snap': _pick(ramp_snaps, -2, lunch_snapshots, 8),
                'rec_type': 'labor',
                'priority': 'low',
                'title': 'Plan staggered breaks after peak subsides',
                'description': (
                    'Once the current rush subsides, front counter staff should take staggered breaks '
                    'to ensure everyone is fresh for dinner. Schedule 15-minute breaks in rotation.'
                ),
                'rationale': (
                    'Staff have been at high utilization since 11:00 AM. Break rotation during '
                    'afternoon lull ensures compliance and prevents fatigue-related errors during dinner.'
                ),
                'suggested_action': 'After orders drop below 25/hr, send front staff on 15-minute staggered breaks. Maintain 2 staff minimum.',
                'is_active': False,
            },
            {
                'snap': _pick(peak_snaps, 1, lunch_snapshots, 14),
                'rec_type': 'inventory',
                'priority': 'low',
                'title': 'Restock cup and napkin stations when possible',
                'description': (
                    'Large cups at 200 of 500 par (40%) and napkins at 350 of 1000 par (35%). '
                    'Restocking during the next lull prevents interruption during dinner service.'
                ),
                'rationale': (
                    'Estimated cup usage: 80/hr during peak. Napkin usage: 120/hr. '
                    'Current levels will last approximately 2.5 hours. Dinner rush starts in ~3 hours.'
                ),
                'suggested_action': 'Have one front staff restock cup dispenser, napkin holders, and condiment station from back storage during next slow moment.',
                'is_active': False,
            },
            {
                'snap': _pick(peak_snaps, 2, lunch_snapshots, 15),
                'rec_type': 'inventory',
                'priority': 'low',
                'title': 'Conduct inventory audit before dinner shift',
                'description': (
                    'Multiple items dropped below thresholds during lunch. A 10-minute physical count '
                    'of critical items will ensure accurate reorder quantities and prevent dinner stockouts.'
                ),
                'rationale': (
                    'Chicken, fries, and cups all hit low levels during peak. '
                    'System estimates may drift from actuals during high-volume periods. '
                    'Accurate counts are needed for dinner planning and potential emergency orders.'
                ),
                'suggested_action': 'After rush subsides, assign one team member to count: chicken breast, burger patties, french fries, lettuce, large cups. Update POS inventory.',
                'is_active': False,
            },
        ]

        for rd in rec_defs:
            rec = Recommendation(
                shift_id=downtown_lunch.shift_id,
                snapshot_id=rd['snap'].snapshot_id,
                rec_type=rd['rec_type'],
                priority=rd['priority'],
                title=rd['title'],
                description=rd['description'],
                rationale=rd['rationale'],
                suggested_action=rd['suggested_action'],
                is_active=rd['is_active'],
                created_at=rd['snap'].captured_at + timedelta(seconds=random.randint(10, 60)),
            )
            db.session.add(rec)
            recommendations.append(rec)

    # --- Historical recommendations spread across 14 days ---
    historical_rec_templates = [
        {
            'rec_type': 'labor',
            'priority': 'high',
            'title': 'Reassign staff during peak',
            'description': 'Kitchen falling behind during lunch peak. Reassigning front staff to kitchen will improve throughput.',
            'rationale': 'Ticket times exceeded 150s threshold during peak hours.',
            'suggested_action': 'Move one front counter staff to grill station.',
        },
        {
            'rec_type': 'inventory',
            'priority': 'high',
            'title': 'Emergency restock needed',
            'description': 'Key inventory items below critical threshold. Immediate restocking required.',
            'rationale': 'Multiple items below 20% par level during service.',
            'suggested_action': 'Place emergency order with distributor.',
        },
        {
            'rec_type': 'labor',
            'priority': 'medium',
            'title': 'Call in additional staff',
            'description': 'Current staffing insufficient for projected demand.',
            'rationale': 'Order-to-staff ratio exceeds recommended threshold.',
            'suggested_action': 'Call in one off-duty team member.',
        },
        {
            'rec_type': 'prep',
            'priority': 'medium',
            'title': 'Begin next-shift prep early',
            'description': 'Current rush subsiding. Use downtime to prep for next shift.',
            'rationale': 'Order volume declining; next shift prep window available.',
            'suggested_action': 'Assign one staff to prep station.',
        },
        {
            'rec_type': 'inventory',
            'priority': 'medium',
            'title': 'Fries supply running low',
            'description': 'French fry inventory approaching critical levels.',
            'rationale': 'Fries at 25% of par with 2 hours of service remaining.',
            'suggested_action': 'Start prepping additional batch immediately.',
        },
        {
            'rec_type': 'labor',
            'priority': 'low',
            'title': 'Reduce front counter staffing',
            'description': 'Front counter overstaffed for current demand level.',
            'rationale': 'Low dine-in volume relative to staff count.',
            'suggested_action': 'Send one front staff on break.',
        },
    ]

    # Get all Dallas shifts from history (not today)
    historical_dallas_shifts = [
        s for s in shifts
        if s.restaurant.city == 'Dallas' and s.shift_date != today
        and s.shift_type in ('lunch', 'dinner')
    ]

    for shift in historical_dallas_shifts:
        # Get snapshots for this shift
        shift_snaps = OperationalSnapshot.query.filter_by(shift_id=shift.shift_id).all()
        if not shift_snaps:
            continue

        # 2-4 recommendations per historical shift
        num_recs = random.randint(2, 4)
        chosen_templates = random.sample(historical_rec_templates, min(num_recs, len(historical_rec_templates)))

        for template in chosen_templates:
            snap = random.choice(shift_snaps)
            is_active = random.random() < 0.2  # 20% still active (unresolved)
            rec = Recommendation(
                shift_id=shift.shift_id,
                snapshot_id=snap.snapshot_id,
                rec_type=template['rec_type'],
                priority=template['priority'],
                title=template['title'],
                description=template['description'],
                rationale=template['rationale'],
                suggested_action=template['suggested_action'],
                is_active=is_active,
                created_at=snap.captured_at + timedelta(seconds=random.randint(10, 120)),
            )
            db.session.add(rec)
            recommendations.append(rec)

    db.session.commit()
    return recommendations


def seed_recommendation_actions(recommendations, users_map, shifts):
    """Create manager responses for recommendations."""
    today = date.today()

    # Today's Downtown lunch actions (same as before for the first 10)
    downtown_lunch = None
    for s in shifts:
        if s.shift_type == 'lunch' and s.restaurant.city == 'Dallas' and s.shift_date == today:
            downtown_lunch = s
            break

    today_recs = [r for r in recommendations if downtown_lunch and r.shift_id == downtown_lunch.shift_id]
    historical_recs = [r for r in recommendations if not downtown_lunch or r.shift_id != downtown_lunch.shift_id]

    if downtown_lunch and today_recs:
        manager = next(
            u for u in users_map[downtown_lunch.restaurant_id] if u.role == 'manager'
        )
        action_defs = [
            (0, 'accepted', 'Moving Tyler from register 2 to drive-thru window 2'),
            (1, 'accepted', 'Pulled 40 chicken from freezer, calling supplier for emergency delivery'),
            (2, 'deferred', 'Monitoring queue — will open window 2 if it hits 18 vehicles'),
            (3, 'deferred', 'Will decide in 30 minutes based on afternoon trend'),
            (5, 'accepted', 'Assigned Maria to start dinner prep at station 3'),
            (8, 'rejected', 'Morning crew already restocked — levels are fine'),
        ]
        for idx, response, notes in action_defs:
            if idx < len(today_recs):
                action = RecommendationAction(
                    recommendation_id=today_recs[idx].recommendation_id,
                    user_id=manager.user_id,
                    response_type=response,
                    notes=notes,
                    responded_at=today_recs[idx].created_at + timedelta(minutes=random.randint(1, 5)),
                )
                db.session.add(action)
                if response in ('accepted', 'rejected'):
                    today_recs[idx].is_active = False

    # Historical recommendation actions: respond to ~70% of historical recs
    response_types = ['accepted', 'accepted', 'accepted', 'deferred', 'rejected']
    notes_options = [
        'Handled by shift manager',
        'Adjustment made',
        'Rebalanced staff per recommendation',
        'Order placed with supplier',
        'Will monitor situation',
        'Already resolved',
        'Not applicable for this shift',
    ]

    for rec in historical_recs:
        if rec.is_active:
            continue  # Skip still-active ones
        if random.random() < 0.70:
            # Find the manager for this restaurant
            shift = next((s for s in shifts if s.shift_id == rec.shift_id), None)
            if not shift:
                continue
            restaurant_users = users_map.get(shift.restaurant_id, [])
            manager = next((u for u in restaurant_users if u.role == 'manager'), None)
            if not manager:
                continue

            response = random.choice(response_types)
            action = RecommendationAction(
                recommendation_id=rec.recommendation_id,
                user_id=manager.user_id,
                response_type=response,
                notes=random.choice(notes_options),
                responded_at=rec.created_at + timedelta(minutes=random.randint(2, 30)),
            )
            db.session.add(action)

    db.session.commit()


def seed_alerts(shifts, lunch_snapshots, users_map):
    """Create alerts spread across 14 days.

    Today's Downtown lunch gets detailed alerts.
    Historical days get 1-3 alerts each.
    """
    today = date.today()

    # --- Today's Downtown lunch: detailed alerts (same as before) ---
    downtown_lunch = None
    for s in shifts:
        if s.shift_type == 'lunch' and s.restaurant.city == 'Dallas' and s.shift_date == today:
            downtown_lunch = s
            break

    if downtown_lunch and lunch_snapshots:
        manager = next(
            u for u in users_map[downtown_lunch.restaurant_id] if u.role == 'manager'
        )
        peak_snaps = [s for s in lunch_snapshots if s.avg_ticket_time_sec >= 150]
        ramp_snaps = [s for s in lunch_snapshots if s.avg_ticket_time_sec < 150]

        def _apick(lst, idx, fallback_lst, fallback_idx):
            if len(lst) > idx:
                return lst[idx]
            return fallback_lst[min(fallback_idx, len(fallback_lst) - 1)]

        _critical_snap = _apick(peak_snaps, 2, lunch_snapshots, 15)
        _surge_snap = _apick(peak_snaps, 1, lunch_snapshots, 14)
        _labor_snap = _apick(peak_snaps, 3, lunch_snapshots, 16)
        _warn_snap = _apick(peak_snaps, 4, lunch_snapshots, 17)
        _front_snap = _apick(ramp_snaps, -1, lunch_snapshots, 10)
        _delivery_snap = _apick(peak_snaps, 5, lunch_snapshots, 18)
        _labor_orders = _labor_snap.total_orders or 52
        _labor_ratio = round(_labor_orders / 3, 1)
        _surge_orders = _surge_snap.total_orders or 45
        _surge_avg = int(_surge_orders * 0.6)
        _surge_pct = round((_surge_orders / max(_surge_avg, 1)) * 100)
        _front_dine = _front_snap.dine_in_orders if _front_snap.dine_in_orders else 4

        alert_defs = [
            # --- CRITICAL alerts ---
            {
                'snap': _surge_snap,
                'alert_type': 'queue_surge',
                'severity': 'critical',
                'message': (
                    f'Drive-thru queue exceeding 15 vehicles. '
                    f'Current queue depth estimated at 16 vehicles with avg wait of 6.2 minutes. '
                    f'Customer abandonment risk is elevated. '
                    f'300s threshold breached.'
                ),
                'ack': False,
            },
            {
                'snap': _critical_snap,
                'alert_type': 'ticket_time_critical',
                'severity': 'critical',
                'message': (
                    f'Kitchen ticket time at 312 seconds — 4x above 78s target. '
                    f'Current avg ticket time: 312s '
                    f'across {_critical_snap.total_orders or 48} active orders. '
                    f'300s threshold breached. Immediate kitchen intervention required.'
                ),
                'ack': True,
            },
            {
                'snap': _labor_snap,
                'alert_type': 'labor_imbalance',
                'severity': 'critical',
                'message': (
                    f'Kitchen severely understaffed: 3 staff handling '
                    f'{_labor_orders}+ orders/hr '
                    f'(ratio: {_labor_ratio}:1, threshold: 10:1). '
                    f'Ticket times accelerating. Reallocate staff immediately.'
                ),
                'ack': False,
            },
            # --- WARNING alerts ---
            {
                'snap': _apick(peak_snaps, 4, lunch_snapshots, 17),
                'alert_type': 'stockout_risk',
                'severity': 'warning',
                'message': (
                    'Chicken inventory below 15% of par level — only 14 pieces remaining '
                    'vs 100 par. At current consumption rate of ~2.1 pieces/min, '
                    'projected stockout in approximately 7 minutes.'
                ),
                'ack': False,
            },
            {
                'snap': _front_snap,
                'alert_type': 'labor_overstaffed_front',
                'severity': 'warning',
                'message': (
                    f'Front counter overstaffed — {_front_snap.front_staff or 3} staff for '
                    f'{_front_dine} dine-in orders '
                    f'(ratio: {round(_front_dine / max(_front_snap.front_staff or 3, 1), 1)}:1, '
                    f'threshold: 3.0:1). '
                    f'Consider reallocating 1 staff to drive-thru or kitchen.'
                ),
                'ack': True,
            },
            {
                'snap': _warn_snap,
                'alert_type': 'ticket_time_warning',
                'severity': 'warning',
                'message': (
                    f'Average ticket time is '
                    f'{_warn_snap.avg_ticket_time_sec or 195}s, exceeding the '
                    f'180s warning threshold. '
                    f'Trending upward for last 15 minutes. Monitor closely to prevent further degradation.'
                ),
                'ack': True,
            },
            # --- INFO alerts ---
            {
                'snap': _delivery_snap,
                'alert_type': 'demand_surge',
                'severity': 'info',
                'message': (
                    f'Delivery orders trending 20% above forecast — '
                    f'{_delivery_snap.delivery_orders or 12} delivery orders vs '
                    f'{int((_delivery_snap.delivery_orders or 12) * 0.83)} predicted. '
                    f'Consider pre-staging packaging and coordinating with delivery drivers.'
                ),
                'ack': True,
            },
            {
                'snap': _apick(peak_snaps, 0, lunch_snapshots, 13),
                'alert_type': 'stockout_risk',
                'severity': 'info',
                'message': (
                    'French fries at 25% of daily par level (20 lbs remaining). '
                    'Current usage rate is moderate. Next prep batch recommended within 30 minutes.'
                ),
                'ack': True,
            },
        ]

        for ad in alert_defs:
            alert = Alert(
                shift_id=downtown_lunch.shift_id,
                snapshot_id=ad['snap'].snapshot_id,
                alert_type=ad['alert_type'],
                severity=ad['severity'],
                message=ad['message'],
                is_acknowledged=ad['ack'],
                acknowledged_by=manager.user_id if ad['ack'] else None,
                created_at=ad['snap'].captured_at + timedelta(seconds=random.randint(5, 30)),
                acknowledged_at=(ad['snap'].captured_at + timedelta(minutes=random.randint(2, 8))) if ad['ack'] else None,
            )
            db.session.add(alert)

    # --- Historical alerts spread across 14 days ---
    historical_alert_templates = [
        {
            'alert_type': 'ticket_time_warning',
            'severity': 'warning',
            'message': 'Average ticket time is {ticket}s, exceeding the 180s warning threshold. Monitor closely to prevent further degradation.',
        },
        {
            'alert_type': 'ticket_time_critical',
            'severity': 'critical',
            'message': 'Drive-thru average wait time exceeds 5 minutes. Current avg ticket time: {ticket}s across {orders} active orders. 300s threshold breached.',
        },
        {
            'alert_type': 'queue_surge',
            'severity': 'warning',
            'message': 'Total order queue is {pct}% above the 30-minute trailing average ({orders} orders vs {avg} avg). 150% threshold breached.',
        },
        {
            'alert_type': 'labor_imbalance',
            'severity': 'critical',
            'message': 'Kitchen understaffed: {staff} staff handling {orders}+ orders/hr (ratio: {ratio}:1, threshold: 10:1).',
        },
        {
            'alert_type': 'stockout_risk',
            'severity': 'warning',
            'message': 'chicken_breast at {pct}% of daily par level ({qty} pieces remaining). Estimated depletion imminent at current rate.',
        },
        {
            'alert_type': 'labor_overstaffed_front',
            'severity': 'info',
            'message': 'Front counter overstaffed relative to current demand. {staff} staff for {orders} dine-in orders (consider rebalancing).',
        },
        {
            'alert_type': 'demand_surge',
            'severity': 'info',
            'message': 'Delivery orders trending {pct}% above forecast ({orders} orders vs {avg} predicted). Consider pre-staging packaging.',
        },
    ]

    # Get Dallas lunch/dinner shifts from history
    historical_dallas_shifts = [
        s for s in shifts
        if s.restaurant.city == 'Dallas' and s.shift_date != today
        and s.shift_type in ('lunch', 'dinner')
    ]

    total_historical_alerts = 0
    for shift in historical_dallas_shifts:
        shift_snaps = OperationalSnapshot.query.filter_by(shift_id=shift.shift_id).all()
        if not shift_snaps:
            continue

        manager = next(
            u for u in users_map[shift.restaurant_id] if u.role == 'manager'
        )

        # 1-3 alerts per historical shift
        num_alerts = random.randint(1, 3)
        chosen_templates = random.sample(historical_alert_templates, min(num_alerts, len(historical_alert_templates)))

        for template in chosen_templates:
            snap = random.choice(shift_snaps)
            is_ack = random.random() < 0.7  # 70% acknowledged

            # Fill in template values
            orders = snap.total_orders or random.randint(30, 55)
            ticket = snap.avg_ticket_time_sec or random.randint(150, 280)
            message = template['message'].format(
                ticket=ticket,
                orders=orders,
                pct=random.randint(155, 200),
                avg=int(orders * 0.6),
                staff=random.choice([2, 3]),
                ratio=round(orders / 3, 1),
                qty=random.randint(8, 20),
            )

            alert = Alert(
                shift_id=shift.shift_id,
                snapshot_id=snap.snapshot_id,
                alert_type=template['alert_type'],
                severity=template['severity'],
                message=message,
                is_acknowledged=is_ack,
                acknowledged_by=manager.user_id if is_ack else None,
                created_at=snap.captured_at + timedelta(seconds=random.randint(5, 60)),
                acknowledged_at=(snap.captured_at + timedelta(minutes=random.randint(2, 15))) if is_ack else None,
            )
            db.session.add(alert)
            total_historical_alerts += 1

    db.session.commit()
    return total_historical_alerts


def seed_settings(restaurants):
    """Create default threshold settings for each restaurant."""
    for restaurant in restaurants:
        settings = Settings(
            restaurant_id=restaurant.restaurant_id,
            queue_surge=1.50,
            low_inventory=0.20,
            labor_imbalance=10.0,
            ticket_time_max=300,
        )
        db.session.add(settings)
    db.session.commit()
    return len(restaurants)


def seed_staff(restaurants):
    """Create staff members and schedules for the Downtown Dallas restaurant."""
    today = date.today()
    dallas = restaurants[0]  # Downtown Dallas is the first restaurant

    staff_defs = [
        ('Maria', 'Rodriguez', 'Shift Lead', '214-555-0101', 'maria.r@dallas.opsync.com', date(2024, 3, 15)),
        ('James', 'Chen', 'Line Cook', '214-555-0102', 'james.c@dallas.opsync.com', date(2024, 6, 20)),
        ('Aisha', 'Thompson', 'Cashier', '214-555-0103', 'aisha.t@dallas.opsync.com', date(2024, 9, 1)),
        ('Carlos', 'Mendez', 'Prep Cook', '214-555-0104', 'carlos.m@dallas.opsync.com', date(2024, 1, 10)),
        ('Sarah', 'Kim', 'Drive-Thru', '214-555-0105', 'sarah.k@dallas.opsync.com', date(2025, 2, 14)),
        ('Devon', 'Washington', 'Line Cook', '214-555-0106', 'devon.w@dallas.opsync.com', date(2024, 11, 5)),
        ('Emily', 'Nguyen', 'Cashier', '214-555-0107', 'emily.n@dallas.opsync.com', date(2025, 4, 22)),
        ('Marcus', 'Johnson', 'Dishwasher', '214-555-0108', 'marcus.j@dallas.opsync.com', date(2025, 1, 8)),
        ('Priya', 'Patel', 'Shift Lead', '214-555-0109', 'priya.p@dallas.opsync.com', date(2024, 5, 30)),
        ('Tyler', 'Brooks', 'Prep Cook', '214-555-0110', 'tyler.b@dallas.opsync.com', date(2025, 3, 17)),
        ('Jessica', 'Ramirez', 'Drive-Thru', '214-555-0111', 'jessica.r@dallas.opsync.com', date(2024, 8, 12)),
        ('Daniel', "O'Brien", 'Line Cook', '214-555-0112', 'daniel.o@dallas.opsync.com', date(2025, 5, 1)),
    ]

    # Position-based shift patterns: (shift_type, start_time, end_time, hours)
    shift_patterns = {
        'Shift Lead':  ('morning', '06:00', '14:00', 8.0),
        'Line Cook':   ('morning', '06:00', '14:00', 8.0),  # default, will rotate
        'Cashier':     ('afternoon', '11:00', '19:00', 8.0),
        'Prep Cook':   ('morning', '06:00', '14:00', 8.0),
        'Drive-Thru':  ('afternoon', '11:00', '19:00', 8.0),
        'Dishwasher':  ('evening', '16:00', '23:00', 7.0),
    }

    # Alternate patterns for line cooks to rotate shifts
    line_cook_rotations = [
        ('morning', '06:00', '14:00', 8.0),
        ('afternoon', '11:00', '19:00', 8.0),
        ('evening', '16:00', '23:00', 7.0),
    ]

    members = []
    for first, last, position, phone, email, hire_date in staff_defs:
        member = StaffMember(
            restaurant_id=dallas.restaurant_id,
            first_name=first,
            last_name=last,
            position=position,
            phone=phone,
            email=email,
            hire_date=hire_date,
            status='active',
        )
        db.session.add(member)
        members.append(member)

    db.session.commit()

    # Called-out entries: assign 1-2 called_out days across all staff over the 30-day window
    # Pick specific (member_index, day_offset) pairs for called_out
    called_out_entries = {
        (1, 5),   # James Chen called out 5 days ago
        (6, 12),  # Emily Nguyen called out 12 days ago
        (4, 20),  # Sarah Kim called out 20 days ago
    }

    # Generate schedules for past 30 days + rest of current week
    # Find the Monday of the current week
    current_monday = today - timedelta(days=today.weekday())
    current_sunday = current_monday + timedelta(days=6)

    # Start from 30 days ago
    start_date = today - timedelta(days=30)

    schedule_count = 0
    for member_idx, member in enumerate(members):
        position = member.position
        base_pattern = shift_patterns[position]

        # Each employee has a consistent set of days off per week
        # Assign 2-3 off days per week, varying by employee
        # Use member_idx to create different day-off patterns
        off_day_sets = [
            {0, 4},     # Mon, Fri off
            {2, 6},     # Wed, Sun off
            {1, 5},     # Tue, Sat off
            {3, 6},     # Thu, Sun off
            {0, 3},     # Mon, Thu off
            {5, 6},     # Sat, Sun off
            {1, 4},     # Tue, Fri off
            {2, 5},     # Wed, Sat off
            {0, 6},     # Mon, Sun off
            {3, 5},     # Thu, Sat off
            {1, 6},     # Tue, Sun off
            {2, 4},     # Wed, Fri off
        ]
        off_days = off_day_sets[member_idx % len(off_day_sets)]

        current_date = start_date
        while current_date <= current_sunday:
            weekday = current_date.weekday()

            # Check if this is a called_out day
            day_offset = (today - current_date).days
            is_called_out = (member_idx, day_offset) in called_out_entries

            if is_called_out:
                # Called out - they were scheduled but called out
                shift_type, start_time, end_time, hours = base_pattern
                schedule = StaffSchedule(
                    staff_id=member.staff_id,
                    date=current_date,
                    shift_type=shift_type,
                    start_time=start_time,
                    end_time=end_time,
                    status='called_out',
                    hours=0,
                )
            elif weekday in off_days:
                # Day off
                schedule = StaffSchedule(
                    staff_id=member.staff_id,
                    date=current_date,
                    shift_type=None,
                    start_time=None,
                    end_time=None,
                    status='off',
                    hours=0,
                )
            else:
                # Working day - determine shift based on position
                if position == 'Line Cook':
                    # Rotate line cooks through different shifts based on week
                    week_num = current_date.isocalendar()[1]
                    rotation_idx = (member_idx + week_num) % len(line_cook_rotations)
                    shift_type, start_time, end_time, hours = line_cook_rotations[rotation_idx]
                else:
                    shift_type, start_time, end_time, hours = base_pattern

                # Determine status: past = completed, today/future = scheduled
                if current_date < today:
                    status = 'completed'
                else:
                    status = 'scheduled'

                schedule = StaffSchedule(
                    staff_id=member.staff_id,
                    date=current_date,
                    shift_type=shift_type,
                    start_time=start_time,
                    end_time=end_time,
                    status=status,
                    hours=hours,
                )

            db.session.add(schedule)
            schedule_count += 1
            current_date += timedelta(days=1)

    db.session.commit()
    return members, schedule_count


def seed_all():
    """Run the complete seed pipeline."""
    print("Starting database seed...")
    clear_all_data()

    restaurants = seed_restaurants()
    print(f"  Created {len(restaurants)} restaurants")

    settings_count = seed_settings(restaurants)
    print(f"  Created {settings_count} settings records")

    users_map = seed_users(restaurants)
    total_users = sum(len(v) for v in users_map.values())
    print(f"  Created {total_users} users")

    shifts, shifts_by_day = seed_shifts(restaurants, users_map)
    print(f"  Created {len(shifts)} shifts (14 days x 3 restaurants)")

    snapshots, lunch_snapshots = seed_snapshots(shifts)
    print(f"  Created {len(snapshots)} operational snapshots")

    recommendations = seed_recommendations(shifts, lunch_snapshots)
    print(f"  Created {len(recommendations)} recommendations")

    seed_recommendation_actions(recommendations, users_map, shifts)
    print(f"  Created recommendation actions")

    historical_alert_count = seed_alerts(shifts, lunch_snapshots, users_map)
    print(f"  Created 8 today alerts + {historical_alert_count} historical alerts")

    staff_members, schedule_count = seed_staff(restaurants)
    print(f"  Created {len(staff_members)} staff members with {schedule_count} schedule entries")

    print("\nDatabase seed complete!")
    print("  Test login: admin@dallas.opsync.com / admin123")


if __name__ == '__main__':
    app = create_app('development')
    with app.app_context():
        db.create_all()
        seed_all()
