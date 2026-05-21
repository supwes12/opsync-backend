"""Database seeding script with realistic restaurant operational data."""

import json
import random
from datetime import datetime, date, time, timedelta

from app import create_app
from app.extensions import db
from app.models import (
    Restaurant, User, Shift, OperationalSnapshot,
    Recommendation, RecommendationAction, Alert
)

random.seed(42)


def clear_all_data():
    """Drop all data in reverse dependency order."""
    RecommendationAction.query.delete()
    Alert.query.delete()
    Recommendation.query.delete()
    OperationalSnapshot.query.delete()
    Shift.query.delete()
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
    """Create shifts for today — 3 per Downtown, 2 per Suburban/Airport."""
    today = date.today()
    shifts = []

    for restaurant in restaurants:
        restaurant_users = users_map[restaurant.restaurant_id]
        manager = next(u for u in restaurant_users if u.role == 'manager')

        if restaurant.city == 'Dallas':
            shift_defs = [
                ('morning', 6, 0, 12, 0, 'completed'),
                ('lunch', 11, 0, 17, 0, 'active'),
                ('dinner', 16, 0, 23, 0, 'active'),
            ]
        elif restaurant.city == 'Plano':
            shift_defs = [
                ('morning', 7, 0, 13, 0, 'completed'),
                ('lunch', 12, 0, 18, 0, 'active'),
            ]
        else:
            shift_defs = [
                ('morning', 5, 0, 11, 0, 'completed'),
                ('lunch', 10, 0, 16, 0, 'active'),
            ]

        for shift_type, sh, sm, eh, em, status in shift_defs:
            shift = Shift(
                restaurant_id=restaurant.restaurant_id,
                manager_id=manager.user_id,
                shift_date=today,
                start_time=datetime(today.year, today.month, today.day, sh, sm),
                end_time=datetime(today.year, today.month, today.day, eh, em),
                shift_type=shift_type,
                status=status,
            )
            db.session.add(shift)
            shifts.append(shift)

    db.session.commit()
    return shifts


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


def seed_snapshots(shifts):
    """Create operational snapshots — detailed for Downtown lunch, lighter for others."""
    snapshots = []
    today = date.today()

    downtown_lunch = next(
        s for s in shifts if s.shift_type == 'lunch' and s.restaurant.city == 'Dallas'
    )
    downtown_morning = next(
        s for s in shifts if s.shift_type == 'morning' and s.restaurant.city == 'Dallas'
    )

    # --- Downtown morning shift: 10 snapshots (7:00–8:15 AM) ---
    for i in range(10):
        t = datetime(today.year, today.month, today.day, 7, 0) + timedelta(minutes=i * 10)
        total = random.randint(3, 18)
        dt = int(total * 0.25)
        dr = int(total * 0.40)
        pk = int(total * 0.20)
        dl = total - dt - dr - pk
        snap = OperationalSnapshot(
            shift_id=downtown_morning.shift_id,
            captured_at=t,
            total_orders=total,
            dine_in_orders=dt,
            drive_thru_orders=dr,
            pickup_orders=pk,
            delivery_orders=dl,
            avg_ticket_time_sec=random.randint(75, 120),
            staff_count=5,
            kitchen_staff=2,
            front_staff=3,
        )
        snap.inventory = _make_inventory('ramp', i * 10)
        db.session.add(snap)
        snapshots.append(snap)

    # --- Downtown lunch shift: 36 snapshots every 5 min (11:00 AM – 2:00 PM) ---
    lunch_snapshots = []
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
            shift_id=downtown_lunch.shift_id,
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
        snap.inventory = _make_inventory(phase, minutes_in if phase == 'ramp' else minutes_in - 60 if phase == 'peak' else minutes_in - 120)
        db.session.add(snap)
        snapshots.append(snap)
        lunch_snapshots.append(snap)

    # --- Other active shifts: 8 snapshots each ---
    other_active = [s for s in shifts if s.status == 'active' and s.shift_id != downtown_lunch.shift_id]
    for shift in other_active:
        for i in range(8):
            t = shift.start_time + timedelta(minutes=i * 15)
            total = random.randint(8, 30)
            dr = int(total * 0.35)
            dt = int(total * 0.30)
            pk = int(total * 0.20)
            dl = total - dr - dt - pk
            snap = OperationalSnapshot(
                shift_id=shift.shift_id,
                captured_at=t,
                total_orders=total,
                dine_in_orders=dt,
                drive_thru_orders=dr,
                pickup_orders=pk,
                delivery_orders=dl,
                avg_ticket_time_sec=random.randint(80, 160),
                staff_count=random.choice([5, 6]),
                kitchen_staff=3,
                front_staff=random.choice([2, 3]),
            )
            snap.inventory = _make_inventory('ramp', i * 15)
            db.session.add(snap)
            snapshots.append(snap)

    db.session.commit()
    return snapshots, lunch_snapshots


def seed_recommendations(shifts, lunch_snapshots):
    """Create 10 recommendations linked to Downtown lunch shift snapshots."""
    downtown_lunch = next(
        s for s in shifts if s.shift_type == 'lunch' and s.restaurant.city == 'Dallas'
    )
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

    recommendations = []
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

    db.session.commit()
    return recommendations


def seed_recommendation_actions(recommendations, users_map, shifts):
    """Create manager responses for 5 recommendations."""
    downtown_lunch = next(
        s for s in shifts if s.shift_type == 'lunch' and s.restaurant.city == 'Dallas'
    )
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
        if idx < len(recommendations):
            action = RecommendationAction(
                recommendation_id=recommendations[idx].recommendation_id,
                user_id=manager.user_id,
                response_type=response,
                notes=notes,
                responded_at=recommendations[idx].created_at + timedelta(minutes=random.randint(1, 5)),
            )
            db.session.add(action)
            if response in ('accepted', 'rejected'):
                recommendations[idx].is_active = False

    db.session.commit()


def seed_alerts(shifts, lunch_snapshots, users_map):
    """Create threshold-triggered alerts for Downtown lunch shift."""
    downtown_lunch = next(
        s for s in shifts if s.shift_type == 'lunch' and s.restaurant.city == 'Dallas'
    )
    manager = next(
        u for u in users_map[downtown_lunch.restaurant_id] if u.role == 'manager'
    )

    peak_snaps = [s for s in lunch_snapshots if s.avg_ticket_time_sec >= 150]
    cooldown_snaps = [s for s in lunch_snapshots if s.avg_ticket_time_sec < 130]

    alert_defs = [
        {
            'snap': peak_snaps[2] if len(peak_snaps) > 2 else lunch_snapshots[15],
            'alert_type': 'queue_surge',
            'severity': 'critical',
            'message': 'Drive-thru avg wait time exceeds 5 minutes',
            'ack': True,
        },
        {
            'snap': peak_snaps[1] if len(peak_snaps) > 1 else lunch_snapshots[14],
            'alert_type': 'queue_surge',
            'severity': 'warning',
            'message': 'Total order queue 50% above 30-min average',
            'ack': True,
        },
        {
            'snap': peak_snaps[3] if len(peak_snaps) > 3 else lunch_snapshots[17],
            'alert_type': 'labor_imbalance',
            'severity': 'critical',
            'message': 'Kitchen understaffed: 3 staff handling 50+ orders/hr',
            'ack': False,
        },
        {
            'snap': peak_snaps[4] if len(peak_snaps) > 4 else lunch_snapshots[19],
            'alert_type': 'stockout_risk',
            'severity': 'warning',
            'message': 'Chicken breast at 15% of daily par level',
            'ack': False,
        },
        {
            'snap': peak_snaps[0] if peak_snaps else lunch_snapshots[13],
            'alert_type': 'stockout_risk',
            'severity': 'info',
            'message': 'French fries at 25% of daily par level',
            'ack': True,
        },
        {
            'snap': cooldown_snaps[0] if cooldown_snaps else lunch_snapshots[25],
            'alert_type': 'labor_imbalance',
            'severity': 'warning',
            'message': 'Front counter overstaffed relative to current demand',
            'ack': False,
        },
        {
            'snap': peak_snaps[0] if peak_snaps else lunch_snapshots[12],
            'alert_type': 'queue_surge',
            'severity': 'warning',
            'message': 'Drive-thru ticket time trending above 3-minute threshold',
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

    db.session.commit()


def seed_all():
    """Run the complete seed pipeline."""
    print("Starting database seed...")
    clear_all_data()

    restaurants = seed_restaurants()
    print(f"  Created {len(restaurants)} restaurants")

    users_map = seed_users(restaurants)
    total_users = sum(len(v) for v in users_map.values())
    print(f"  Created {total_users} users")

    shifts = seed_shifts(restaurants, users_map)
    print(f"  Created {len(shifts)} shifts")

    snapshots, lunch_snapshots = seed_snapshots(shifts)
    print(f"  Created {len(snapshots)} operational snapshots")

    recommendations = seed_recommendations(shifts, lunch_snapshots)
    print(f"  Created {len(recommendations)} recommendations")

    seed_recommendation_actions(recommendations, users_map, shifts)
    print(f"  Created 5 recommendation actions")

    seed_alerts(shifts, lunch_snapshots, users_map)
    print(f"  Created 7 alerts")

    print("\nDatabase seed complete!")
    print("  Test login: admin@dallas.opsync.com / admin123")


if __name__ == '__main__':
    app = create_app('development')
    with app.app_context():
        db.create_all()
        seed_all()
