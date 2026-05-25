"""Database seeding script with realistic restaurant operational data."""

import json
import random
from datetime import datetime, date, time, timedelta

from app import create_app
from app.extensions import db
from app.models import (
    Restaurant, User, Shift, OperationalSnapshot,
    Recommendation, RecommendationAction, Alert, Settings
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
    total = max(2, int(base_orders * day_factor + random.randint(-5, 5)))

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

        # Day-to-day variation factor
        day_offset = (today - shift.shift_date).days
        # Slight variation: weekdays busier, older days slightly different
        weekday = shift.shift_date.weekday()
        if weekday in (5, 6):  # weekend
            day_factor = random.uniform(1.05, 1.25)
        else:
            day_factor = random.uniform(0.85, 1.10)

        start_hour = shift.start_time.hour
        end_hour = shift.end_time.hour
        if end_hour <= start_hour:
            end_hour = 23

        # Today's Downtown lunch shift: detailed 5-minute snapshots
        if is_today and is_downtown and shift.shift_type == 'lunch':
            today_downtown_lunch = shift
            for i in range(36):
                t = datetime(today.year, today.month, today.day, 11, 0) + timedelta(minutes=i * 5)
                minutes_in = i * 5

                if minutes_in < 60:
                    phase = 'ramp'
                    base_orders = 5 + int(30 * (minutes_in / 60))
                    base_ticket = 90 + int(50 * (minutes_in / 60))
                    staff, kitchen, front = 6, 3, 3
                elif minutes_in < 120:
                    phase = 'peak'
                    peak_min = minutes_in - 60
                    base_orders = 40 + int(15 * (peak_min / 60))
                    base_ticket = 150 + int(90 * (peak_min / 60))
                    staff, kitchen, front = 6, 3, 3
                else:
                    phase = 'cool'
                    cool_min = minutes_in - 120
                    base_orders = 30 - int(10 * (cool_min / 60))
                    base_ticket = 130 - int(30 * (cool_min / 60))
                    staff, kitchen, front = 5, 3, 2

                total = max(2, base_orders + random.randint(-3, 3))
                dr = max(0, int(total * 0.40) + random.randint(-2, 2))
                dt = max(0, int(total * 0.25) + random.randint(-1, 1))
                pk = max(0, int(total * 0.20) + random.randint(-1, 1))
                dl = max(0, total - dr - dt - pk)
                ticket = max(60, base_ticket + random.randint(-10, 10))

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
                    minutes_in if phase == 'ramp' else minutes_in - 60 if phase == 'peak' else minutes_in - 120,
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
        cooldown_snaps = [s for s in lunch_snapshots if s.avg_ticket_time_sec < 130]

        rec_defs = [
            {
                'snap': peak_snaps[0] if peak_snaps else lunch_snapshots[12],
                'rec_type': 'labor',
                'priority': 'high',
                'title': 'Move 1 staff from front to kitchen',
                'description': 'Kitchen is falling behind on ticket times during lunch peak. Moving one front counter staff to assist with grill and assembly will reduce average ticket time.',
                'rationale': f'Average ticket time has reached {peak_snaps[0].avg_ticket_time_sec if peak_snaps else 180}s, exceeding the 150s threshold with {peak_snaps[0].total_orders if peak_snaps else 40}+ orders in queue.',
                'suggested_action': 'Reassign one front counter team member to kitchen grill station.',
                'is_active': True,
            },
            {
                'snap': peak_snaps[2] if len(peak_snaps) > 2 else lunch_snapshots[15],
                'rec_type': 'labor',
                'priority': 'medium',
                'title': 'Consider calling in additional staff',
                'description': 'Current staffing of 6 is insufficient for sustained 50+ orders per hour. An additional team member would prevent service degradation.',
                'rationale': 'Order volume has exceeded 45 orders with only 6 staff on duty. Industry standard is 1 staff per 8 orders/hr.',
                'suggested_action': 'Call in one off-duty team member for a 3-hour shift.',
                'is_active': True,
            },
            {
                'snap': peak_snaps[3] if len(peak_snaps) > 3 else lunch_snapshots[18],
                'rec_type': 'inventory',
                'priority': 'high',
                'title': 'Chicken breast approaching stockout',
                'description': 'Chicken breast inventory has dropped below 20% of daily par level. At current consumption rate, stockout is projected within 45 minutes.',
                'rationale': 'Current chicken breast: 15 pieces remaining vs 100 par. Consumption rate: ~2 pieces/min during peak.',
                'suggested_action': 'Place emergency order with supplier or pull from freezer backup.',
                'is_active': True,
            },
            {
                'snap': peak_snaps[1] if len(peak_snaps) > 1 else lunch_snapshots[14],
                'rec_type': 'inventory',
                'priority': 'medium',
                'title': 'French fries below threshold',
                'description': 'French fry supply has fallen below 30% of daily par. Consider prepping an additional batch.',
                'rationale': 'Current french fries: 20 lbs remaining vs 80 par. Peak demand continues for estimated 30 more minutes.',
                'suggested_action': 'Start prepping additional fry batch immediately.',
                'is_active': True,
            },
            {
                'snap': cooldown_snaps[0] if cooldown_snaps else lunch_snapshots[24],
                'rec_type': 'prep',
                'priority': 'medium',
                'title': 'Start prepping dinner rush items',
                'description': 'Lunch rush is subsiding. Begin preparation for dinner shift items to ensure smooth transition.',
                'rationale': 'Order volume declining, dinner shift starts in 3 hours. Prep time for key items is 60-90 minutes.',
                'suggested_action': 'Assign one kitchen staff to begin dinner prep: marinate chicken, portion burger patties, prep salad ingredients.',
                'is_active': True,
            },
            {
                'snap': cooldown_snaps[1] if len(cooldown_snaps) > 1 else lunch_snapshots[26],
                'rec_type': 'labor',
                'priority': 'low',
                'title': 'Front counter staff can take break',
                'description': 'Order volume has dropped significantly. Front counter is overstaffed for current demand level.',
                'rationale': 'Current orders at 22/hr with 3 front staff. One can take a 15-minute break without impact.',
                'suggested_action': 'Send one front counter staff on break rotation.',
                'is_active': False,
            },
            {
                'snap': peak_snaps[4] if len(peak_snaps) > 4 else lunch_snapshots[20],
                'rec_type': 'alert',
                'priority': 'high',
                'title': 'Drive-thru queue exceeding 5 minutes',
                'description': 'Drive-thru average wait time has spiked above acceptable levels. Immediate action needed to prevent customer abandonment.',
                'rationale': f'Drive-thru ticket time: {peak_snaps[4].avg_ticket_time_sec if len(peak_snaps) > 4 else 240}s. Target max: 180s. Queue depth estimated at 8+ vehicles.',
                'suggested_action': 'Open second drive-thru window or dedicate one staff to expediting drive-thru orders.',
                'is_active': False,
            },
            {
                'snap': peak_snaps[1] if len(peak_snaps) > 1 else lunch_snapshots[16],
                'rec_type': 'prep',
                'priority': 'low',
                'title': 'Restock cup station',
                'description': 'Large cup inventory is below 50% of par. Restocking now prevents interruption during continued service.',
                'rationale': 'Large cups at 200 of 500 par. Estimated usage: ~80 cups/hour during peak.',
                'suggested_action': 'Have front staff restock cup station from storage during next low point.',
                'is_active': False,
            },
            {
                'snap': peak_snaps[0] if peak_snaps else lunch_snapshots[13],
                'rec_type': 'labor',
                'priority': 'high',
                'title': 'Activate overflow prep station',
                'description': 'Order backlog growing. Opening the secondary prep station will increase throughput by approximately 30%.',
                'rationale': 'Ticket time trending upward with no sign of volume decrease. Secondary station can handle sandwich assembly.',
                'suggested_action': 'Open overflow prep station and assign one staff member from front.',
                'is_active': False,
            },
            {
                'snap': cooldown_snaps[2] if len(cooldown_snaps) > 2 else lunch_snapshots[28],
                'rec_type': 'inventory',
                'priority': 'low',
                'title': 'Review end-of-day inventory counts',
                'description': 'Multiple items dropped below thresholds during lunch. Recommend a full inventory count before dinner rush.',
                'rationale': 'Chicken, fries, and cups all hit low levels. Accurate counts needed for dinner planning.',
                'suggested_action': 'Assign one team member to do a quick physical count of top 5 items.',
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
            (0, 'accepted', 'Moved Sarah to grill station'),
            (1, 'deferred', 'Monitoring for 15 more minutes'),
            (2, 'accepted', 'Placed emergency order with supplier'),
            (6, 'accepted', 'Opened second drive-thru window'),
            (7, 'rejected', 'Already handled by morning crew'),
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
        cooldown_snaps = [s for s in lunch_snapshots if s.avg_ticket_time_sec < 130]

        _critical_snap = peak_snaps[2] if len(peak_snaps) > 2 else lunch_snapshots[15]
        _surge_snap = peak_snaps[1] if len(peak_snaps) > 1 else lunch_snapshots[14]
        _labor_snap = peak_snaps[3] if len(peak_snaps) > 3 else lunch_snapshots[17]
        _warn_snap = peak_snaps[4] if len(peak_snaps) > 4 else (peak_snaps[-1] if peak_snaps else lunch_snapshots[17])
        _front_snap = cooldown_snaps[0] if cooldown_snaps else lunch_snapshots[25]
        _labor_orders = _labor_snap.total_orders or 52
        _labor_ratio = round(_labor_orders / 3, 1)
        _surge_orders = _surge_snap.total_orders or 45
        _surge_avg = int(_surge_orders * 0.6)
        _surge_pct = round((_surge_orders / max(_surge_avg, 1)) * 100)
        _front_dine = _front_snap.dine_in_orders if _front_snap.dine_in_orders else 5

        alert_defs = [
            {
                'snap': _critical_snap,
                'alert_type': 'ticket_time_critical',
                'severity': 'critical',
                'message': (
                    f'Drive-thru average wait time exceeds 5 minutes. '
                    f'Current avg ticket time: 312s '
                    f'across {_critical_snap.total_orders or 48} active orders. '
                    f'300s threshold breached.'
                ),
                'ack': True,
            },
            {
                'snap': _surge_snap,
                'alert_type': 'queue_surge',
                'severity': 'warning',
                'message': (
                    f'Total order queue is {_surge_pct}% above the 30-minute trailing average '
                    f'({_surge_orders} orders vs {_surge_avg} avg). '
                    f'150% threshold breached.'
                ),
                'ack': True,
            },
            {
                'snap': _labor_snap,
                'alert_type': 'labor_imbalance',
                'severity': 'critical',
                'message': (
                    f'Kitchen understaffed: 3 staff handling '
                    f'{_labor_orders}+ orders/hr '
                    f'(ratio: {_labor_ratio}:1, threshold: 10:1).'
                ),
                'ack': False,
            },
            {
                'snap': peak_snaps[4] if len(peak_snaps) > 4 else lunch_snapshots[19],
                'alert_type': 'stockout_risk',
                'severity': 'warning',
                'message': 'chicken_breast at 15% of daily par level (15 pieces remaining). Estimated depletion imminent at current rate.',
                'ack': False,
            },
            {
                'snap': peak_snaps[0] if peak_snaps else lunch_snapshots[13],
                'alert_type': 'stockout_risk',
                'severity': 'info',
                'message': 'french_fries at 25% of daily par level (20 lbs remaining). Estimated depletion imminent at current rate.',
                'ack': True,
            },
            {
                'snap': _front_snap,
                'alert_type': 'labor_overstaffed_front',
                'severity': 'warning',
                'message': (
                    f'Front counter overstaffed relative to current demand. '
                    f'{_front_snap.front_staff or 3} staff for {_front_dine} dine-in orders '
                    f'(ratio: {round(_front_dine / max(_front_snap.front_staff or 3, 1), 1)}:1, '
                    f'threshold: 3.0:1).'
                ),
                'ack': False,
            },
            {
                'snap': _warn_snap,
                'alert_type': 'ticket_time_warning',
                'severity': 'warning',
                'message': (
                    f'Average ticket time is '
                    f'{_warn_snap.avg_ticket_time_sec or 195}s, exceeding the '
                    f'180s warning threshold. Monitor closely to prevent further degradation.'
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
    print(f"  Created 7 today alerts + {historical_alert_count} historical alerts")

    print("\nDatabase seed complete!")
    print("  Test login: admin@dallas.opsync.com / admin123")


if __name__ == '__main__':
    app = create_app('development')
    with app.app_context():
        db.create_all()
        seed_all()
