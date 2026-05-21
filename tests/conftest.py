"""Pytest fixtures for OpSync backend tests."""
from datetime import time

import pytest

from app import create_app
from app.extensions import db as _db
from app.models import Restaurant, User


@pytest.fixture(scope='session')
def app():
    app = create_app('testing')
    with app.app_context():
        _db.create_all()
    yield app


@pytest.fixture(autouse=True)
def cleanup(app):
    with app.app_context():
        yield
        _db.session.rollback()
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def sample_restaurant(app):
    with app.app_context():
        r = Restaurant(
            name='Test Restaurant',
            address='123 Test St',
            city='Dallas',
            state='TX',
            zip_code='75001',
            format_type='drive-thru',
            open_time=time(6, 0),
            close_time=time(22, 0),
        )
        _db.session.add(r)
        _db.session.commit()
        return r.restaurant_id


@pytest.fixture
def sample_user(app, sample_restaurant):
    with app.app_context():
        u = User(
            email='test@test.com',
            first_name='Test',
            last_name='User',
            role='manager',
            restaurant_id=sample_restaurant,
        )
        u.set_password('test123')
        _db.session.add(u)
        _db.session.commit()
        return u.user_id


@pytest.fixture
def admin_user(app, sample_restaurant):
    with app.app_context():
        u = User(
            email='admin@test.com',
            first_name='Admin',
            last_name='User',
            role='admin',
            restaurant_id=sample_restaurant,
        )
        u.set_password('admin123')
        _db.session.add(u)
        _db.session.commit()
        return u.user_id


@pytest.fixture
def auth_headers(client, sample_user):
    resp = client.post('/api/auth/login', json={'email': 'test@test.com', 'password': 'test123'})
    token = resp.get_json()['access_token']
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def admin_headers(client, admin_user):
    resp = client.post('/api/auth/login', json={'email': 'admin@test.com', 'password': 'admin123'})
    token = resp.get_json()['access_token']
    return {'Authorization': f'Bearer {token}'}
