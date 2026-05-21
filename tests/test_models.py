"""Tests for database models."""
from datetime import time

from app.extensions import db
from app.models import Restaurant, User


class TestUserModel:
    def test_password_hashing(self, app):
        with app.app_context():
            r = Restaurant(
                name='Test', address='123 St', city='Dallas',
                state='TX', zip_code='75001', format_type='drive-thru',
                open_time=time(6, 0), close_time=time(22, 0),
            )
            db.session.add(r)
            db.session.commit()

            u = User(
                email='hash@test.com', first_name='Hash', last_name='Test',
                role='viewer', restaurant_id=r.restaurant_id,
            )
            u.set_password('secret')
            db.session.add(u)
            db.session.commit()

            assert u.check_password('secret') is True
            assert u.check_password('wrong') is False

    def test_to_dict_excludes_password(self, app):
        with app.app_context():
            r = Restaurant(
                name='Test', address='123 St', city='Dallas',
                state='TX', zip_code='75001', format_type='drive-thru',
                open_time=time(6, 0), close_time=time(22, 0),
            )
            db.session.add(r)
            db.session.commit()

            u = User(
                email='dict@test.com', first_name='Dict', last_name='Test',
                role='manager', restaurant_id=r.restaurant_id,
            )
            u.set_password('pass')
            db.session.add(u)
            db.session.commit()

            d = u.to_dict()
            assert 'password_hash' not in d
            assert d['email'] == 'dict@test.com'
            assert d['role'] == 'manager'
