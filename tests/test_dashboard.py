"""Tests for dashboard endpoints."""
from datetime import datetime, date

from app.extensions import db
from app.models import Shift, OperationalSnapshot


class TestDashboardCurrent:
    def test_no_active_shift_returns_404(self, client, auth_headers):
        resp = client.get('/api/dashboard/current', headers=auth_headers)
        assert resp.status_code == 404

    def test_with_active_shift_returns_data(self, app, client, sample_restaurant, auth_headers):
        with app.app_context():
            shift = Shift(
                restaurant_id=sample_restaurant,
                shift_date=date.today(),
                start_time=datetime(2026, 5, 13, 6, 0),
                end_time=datetime(2026, 5, 13, 14, 0),
                shift_type='morning',
                status='active',
            )
            db.session.add(shift)
            db.session.commit()
            shift_id = shift.shift_id

            snapshot = OperationalSnapshot(
                shift_id=shift_id,
                captured_at=datetime.utcnow(),
                total_orders=45,
                staff_count=8,
                avg_ticket_time_sec=142,
            )
            db.session.add(snapshot)
            db.session.commit()

        resp = client.get('/api/dashboard/current', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['current_shift']['shift_id'] == shift_id
        assert data['latest_snapshot']['total_orders'] == 45
        assert data['summary']['total_orders'] == 45
        assert data['summary']['staff_count'] == 8

    def test_requires_auth(self, client):
        resp = client.get('/api/dashboard/current')
        assert resp.status_code == 401


class TestDashboardMetrics:
    def test_metrics_requires_shift_id(self, client, auth_headers):
        resp = client.get('/api/dashboard/metrics', headers=auth_headers)
        assert resp.status_code == 400

    def test_metrics_returns_snapshots(self, app, client, sample_restaurant, auth_headers):
        with app.app_context():
            shift = Shift(
                restaurant_id=sample_restaurant,
                shift_date=date.today(),
                start_time=datetime(2026, 5, 13, 6, 0),
                end_time=datetime(2026, 5, 13, 14, 0),
                shift_type='morning',
                status='active',
            )
            db.session.add(shift)
            db.session.commit()
            shift_id = shift.shift_id

            snapshot = OperationalSnapshot(
                shift_id=shift_id,
                captured_at=datetime.utcnow(),
                total_orders=30,
                staff_count=6,
                avg_ticket_time_sec=120,
            )
            db.session.add(snapshot)
            db.session.commit()

        resp = client.get(f'/api/dashboard/metrics?shift_id={shift_id}', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['shift_id'] == shift_id
        assert len(data['snapshots']) == 1
        assert data['snapshots'][0]['total_orders'] == 30
