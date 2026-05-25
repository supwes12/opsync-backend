from flask import Flask
from config import config_by_name
from app.extensions import db, migrate, jwt, bcrypt, cors


def create_app(config_name='development'):
    app = Flask(__name__)
    app.url_map.strict_slashes = False
    app.config.from_object(config_by_name[config_name])

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)
    cors.init_app(app)

    # Import models so SQLAlchemy registers them
    from app import models  # noqa: F401

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
        from app.models import Recommendation, RecommendationAction, Alert, Settings
        from app.models import AuditLog
        return {
            'db': db,
            'Restaurant': Restaurant,
            'User': User,
            'Shift': Shift,
            'OperationalSnapshot': OperationalSnapshot,
            'Recommendation': Recommendation,
            'RecommendationAction': RecommendationAction,
            'Alert': Alert,
            'Settings': Settings,
            'AuditLog': AuditLog,
        }

    @app.cli.command('seed')
    def seed_command():
        """Seed the database with sample data."""
        from app.seed.seed_data import seed_all
        db.create_all()
        seed_all()

    return app
