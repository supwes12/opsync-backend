# CLAUDE.md — Session 1: Project Setup & Environment Configuration

## BEFORE YOU START — Context Protocol

1. **Read `CLAUDE.md`** (the master project context file in this directory)
2. **Read `HANDOFF.md`** — check if any prior sessions have run. If they have, trust what's documented there over what's written in this instruction file.
3. Then proceed with the work below.

## WHEN YOU FINISH — Handoff Protocol

After completing all steps and verification:
1. **Append your handoff section to `HANDOFF.md`** using the template defined in that file
2. Include: every file you created (full paths), any deviations from this plan, verification results, and anything Session 2 needs to know
3. This is **mandatory** — the next session depends on your handoff notes for continuity

---

## Mission

Set up the complete Python/Flask backend project structure for **OpSync — Real-Time Restaurant Intelligence**, a real-time decision support system for quick-service restaurant (QSR) managers. This session creates the skeleton that all other sessions build on.

## Project Name

`opsync-backend`

## Tech Stack (Locked — Do Not Deviate)

| Layer | Technology | Version |
|-------|-----------|---------|
| Language | Python | 3.12+ |
| Web Framework | Flask | 3.0+ |
| ORM | SQLAlchemy | 2.0+ |
| Database (dev) | SQLite | 3 |
| Database (prod) | PostgreSQL | 16+ |
| Auth | JWT (PyJWT) | Latest |
| Password Hashing | bcrypt | Latest |
| Task Queue | Celery | 5.3+ |
| Cache/Broker | Redis | 7.2+ |
| ML | scikit-learn | 1.4+ |
| Data Processing | pandas | 2.1+ |

> **IMPORTANT**: For local development, use **SQLite**. The config must support swapping to PostgreSQL via an environment variable with zero code changes.

## Directory Structure to Create

```
opsync-backend/
├── CLAUDE.md                      # Master project context (copy from CLAUDE-00-MASTER.md)
├── .env.example                   # Template environment variables
├── .gitignore                     # Python/Flask gitignore
├── requirements.txt               # Pinned dependencies
├── config.py                      # App configuration (dev/test/prod)
├── run.py                         # Application entry point
├── wsgi.py                        # WSGI entry point for production
├── app/
│   ├── __init__.py                # Flask app factory (create_app)
│   ├── extensions.py              # SQLAlchemy, JWT, Bcrypt, Celery init
│   ├── models/
│   │   ├── __init__.py            # Import all models
│   │   ├── restaurant.py
│   │   ├── user.py
│   │   ├── shift.py
│   │   ├── operational_snapshot.py
│   │   ├── recommendation.py
│   │   ├── recommendation_action.py
│   │   └── alert.py
│   ├── api/
│   │   ├── __init__.py            # Register all blueprints
│   │   ├── auth.py                # /api/auth/* endpoints
│   │   ├── dashboard.py           # /api/dashboard/* endpoints
│   │   ├── recommendations.py     # /api/recommendations/* endpoints
│   │   ├── alerts.py              # /api/alerts/* endpoints
│   │   ├── restaurants.py         # /api/restaurants/* endpoints
│   │   └── shifts.py              # /api/shifts/* endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py        # Authentication logic
│   │   ├── dashboard_service.py   # Dashboard data aggregation
│   │   ├── recommendation_engine.py  # Recommendation generation
│   │   ├── alert_service.py       # Alert threshold evaluation
│   │   └── forecast_service.py    # Demand forecasting
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── decorators.py          # Auth decorators (jwt_required, role_required)
│   │   ├── errors.py              # Custom error handlers
│   │   └── helpers.py             # UUID generation, datetime utils
│   └── seed/
│       ├── __init__.py
│       └── seed_data.py           # Database seeding script
├── migrations/                    # Flask-Migrate (Alembic) directory
│   └── (auto-generated)
└── tests/
    ├── __init__.py
    ├── conftest.py                # Pytest fixtures (test client, test db)
    ├── test_auth.py
    ├── test_dashboard.py
    └── test_models.py
```

## Step-by-Step Instructions

### Step 1: Create all directories

Create every directory in the structure above. Use `os.makedirs` or `mkdir -p` as needed.

### Step 2: Create `.env.example`

```env
# Flask
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=change-me-to-a-random-secret-key

# Database
# For SQLite (development):
DATABASE_URL=sqlite:///opsync_dev.db
# For PostgreSQL (production):
# DATABASE_URL=postgresql://user:password@localhost:5432/opsync

# JWT
JWT_SECRET_KEY=change-me-to-a-different-secret
JWT_ACCESS_TOKEN_EXPIRES=3600

# Redis (for Celery - optional in dev)
REDIS_URL=redis://localhost:6379/0

# Celery (optional in dev)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Step 3: Create `.gitignore`

Standard Python gitignore including:
- `__pycache__/`, `*.pyc`, `*.pyo`
- `.env`, `*.db` (SQLite files)
- `venv/`, `.venv/`
- `instance/`
- `.pytest_cache/`
- `migrations/versions/` (optional)
- `*.egg-info/`, `dist/`, `build/`

### Step 4: Create `requirements.txt`

```
Flask>=3.0.0
Flask-SQLAlchemy>=3.1.0
Flask-Migrate>=4.0.0
Flask-JWT-Extended>=4.6.0
Flask-Bcrypt>=1.0.1
Flask-CORS>=4.0.0
SQLAlchemy>=2.0.0
PyJWT>=2.8.0
python-dotenv>=1.0.0
marshmallow>=3.20.0
celery[redis]>=5.3.0
redis>=5.0.0
scikit-learn>=1.4.0
pandas>=2.1.0
numpy>=1.26.0
gunicorn>=21.2.0
pytest>=7.4.0
pytest-flask>=1.3.0
```

### Step 5: Create `config.py`

Must implement a configuration class hierarchy:

```python
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-dev-secret')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        seconds=int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES', 3600))
    )

class DevelopmentConfig(Config):
    """Development configuration — SQLite."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 'sqlite:///opsync_dev.db'
    )

class TestingConfig(Config):
    """Testing configuration — in-memory SQLite."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

class ProductionConfig(Config):
    """Production configuration — PostgreSQL."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')

config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
}
```

### Step 6: Create `app/extensions.py`

Initialize all Flask extensions here (do NOT attach to app yet — that happens in the factory):

```python
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
bcrypt = Bcrypt()
cors = CORS()
```

### Step 7: Create `app/__init__.py` — App Factory

```python
from flask import Flask
from config import config_by_name
from app.extensions import db, migrate, jwt, bcrypt, cors

def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)
    cors.init_app(app)

    # Register blueprints
    from app.api import register_blueprints
    register_blueprints(app)

    # Register error handlers
    from app.utils.errors import register_error_handlers
    register_error_handlers(app)

    # Shell context for flask shell
    @app.shell_context_processor
    def make_shell_context():
        from app.models import Restaurant, User, Shift, OperationalSnapshot
        from app.models import Recommendation, RecommendationAction, Alert
        return {
            'db': db,
            'Restaurant': Restaurant,
            'User': User,
            'Shift': Shift,
            'OperationalSnapshot': OperationalSnapshot,
            'Recommendation': Recommendation,
            'RecommendationAction': RecommendationAction,
            'Alert': Alert,
        }

    return app
```

### Step 8: Create `run.py`

```python
import os
from app import create_app

config_name = os.environ.get('FLASK_ENV', 'development')
app = create_app(config_name)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
```

### Step 9: Create `app/api/__init__.py`

```python
from flask import Blueprint

def register_blueprints(app):
    from app.api.auth import auth_bp
    from app.api.dashboard import dashboard_bp
    from app.api.recommendations import recommendations_bp
    from app.api.alerts import alerts_bp
    from app.api.restaurants import restaurants_bp
    from app.api.shifts import shifts_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(recommendations_bp, url_prefix='/api/recommendations')
    app.register_blueprint(alerts_bp, url_prefix='/api/alerts')
    app.register_blueprint(restaurants_bp, url_prefix='/api/restaurants')
    app.register_blueprint(shifts_bp, url_prefix='/api/shifts')
```

### Step 10: Create placeholder files

For every file listed in the directory structure that is NOT fully specified above, create it with:
- Proper imports
- A module docstring explaining its purpose
- Placeholder classes/functions with `pass` or `raise NotImplementedError`
- Blueprint registration for API files: `{name}_bp = Blueprint('{name}', __name__)`

### Step 11: Create `app/utils/errors.py`

```python
from flask import jsonify

def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({'error': 'Bad request', 'message': str(e)}), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({'error': 'Unauthorized', 'message': 'Authentication required'}), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({'error': 'Forbidden', 'message': 'Insufficient permissions'}), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Not found', 'message': 'Resource not found'}), 404

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({'error': 'Internal server error', 'message': 'An unexpected error occurred'}), 500
```

### Step 12: Create `app/utils/decorators.py`

```python
from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt

def role_required(*allowed_roles):
    """Decorator that checks JWT and verifies user role."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if claims.get('role') not in allowed_roles:
                return jsonify({'error': 'Forbidden', 'message': 'Insufficient role'}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator
```

### Step 13: Create `tests/conftest.py`

```python
import pytest
from app import create_app
from app.extensions import db as _db

@pytest.fixture(scope='session')
def app():
    app = create_app('testing')
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()

@pytest.fixture(scope='function')
def db(app):
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.drop_all()

@pytest.fixture(scope='function')
def client(app):
    return app.test_client()
```

## Verification Checklist

After completing all steps, verify:

1. `cd opsync-backend && pip install -r requirements.txt` succeeds
2. `python run.py` starts the Flask dev server without errors
3. `python -c "from app import create_app; app = create_app('testing'); print('OK')"` works
4. All `__init__.py` files exist in every package directory
5. The SQLite database file is created on first run
6. `pytest tests/` runs (tests may be empty but the runner should not crash)

## What NOT To Do

- Do NOT create any frontend/React code
- Do NOT install or configure PostgreSQL
- Do NOT implement full model logic (that's Session 2)
- Do NOT implement full API logic (that's Session 3)
- Do NOT write seed data (that's Session 4)
- Keep model files as stubs with just the class name and `pass`
- Keep API route files as stubs with just the blueprint and placeholder routes
