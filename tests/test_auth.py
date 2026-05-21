"""Tests for authentication endpoints."""


class TestRegister:
    def test_register_success(self, client, sample_restaurant):
        resp = client.post('/api/auth/register', json={
            'email': 'new@test.com',
            'password': 'pass123',
            'first_name': 'New',
            'last_name': 'User',
            'role': 'viewer',
            'restaurant_id': sample_restaurant,
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['user']['email'] == 'new@test.com'
        assert data['user']['role'] == 'viewer'
        assert 'password_hash' not in data['user']

    def test_register_duplicate_email(self, client, sample_restaurant, sample_user):
        resp = client.post('/api/auth/register', json={
            'email': 'test@test.com',
            'password': 'pass123',
            'first_name': 'Dup',
            'last_name': 'User',
            'role': 'viewer',
            'restaurant_id': sample_restaurant,
        })
        assert resp.status_code == 409

    def test_register_missing_fields(self, client):
        resp = client.post('/api/auth/register', json={'email': 'x@x.com'})
        assert resp.status_code == 400

    def test_register_invalid_role(self, client, sample_restaurant):
        resp = client.post('/api/auth/register', json={
            'email': 'bad@test.com',
            'password': 'pass123',
            'first_name': 'Bad',
            'last_name': 'Role',
            'role': 'superadmin',
            'restaurant_id': sample_restaurant,
        })
        assert resp.status_code == 400


class TestLogin:
    def test_login_success(self, client, sample_user):
        resp = client.post('/api/auth/login', json={
            'email': 'test@test.com',
            'password': 'test123',
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'access_token' in data
        assert data['user']['email'] == 'test@test.com'

    def test_login_wrong_password(self, client, sample_user):
        resp = client.post('/api/auth/login', json={
            'email': 'test@test.com',
            'password': 'wrong',
        })
        assert resp.status_code == 401

    def test_login_nonexistent_email(self, client):
        resp = client.post('/api/auth/login', json={
            'email': 'nobody@test.com',
            'password': 'pass',
        })
        assert resp.status_code == 401

    def test_login_missing_fields(self, client):
        resp = client.post('/api/auth/login', json={})
        assert resp.status_code == 400


class TestMe:
    def test_me_with_token(self, client, auth_headers):
        resp = client.get('/api/auth/me', headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()['user']['email'] == 'test@test.com'

    def test_me_without_token(self, client):
        resp = client.get('/api/auth/me')
        assert resp.status_code == 401
