from datetime import datetime

from flask import Blueprint, jsonify


def register_blueprints(app):
    from app.api.auth import auth_bp
    from app.api.dashboard import dashboard_bp
    from app.api.recommendations import recommendations_bp
    from app.api.alerts import alerts_bp
    from app.api.restaurants import restaurants_bp
    from app.api.shifts import shifts_bp
    from app.api.settings import settings_bp
    from app.api.snapshots import snapshots_bp
    from app.api.audit import audit_bp
    from app.api.staff import staff_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(recommendations_bp, url_prefix='/api/recommendations')
    app.register_blueprint(alerts_bp, url_prefix='/api/alerts')
    app.register_blueprint(restaurants_bp, url_prefix='/api/restaurants')
    app.register_blueprint(shifts_bp, url_prefix='/api/shifts')
    app.register_blueprint(settings_bp, url_prefix='/api/settings')
    app.register_blueprint(snapshots_bp, url_prefix='/api/snapshots')
    app.register_blueprint(audit_bp, url_prefix='/api/audit')
    app.register_blueprint(staff_bp, url_prefix='/api/staff')

    # Task 1: Health check endpoint (registered directly on app)
    @app.route('/health', methods=['GET'])
    def health_check():
        from app.extensions import db
        db_status = 'connected'
        try:
            db.session.execute(db.text('SELECT 1'))
        except Exception:
            db_status = 'disconnected'
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': db_status,
        }), 200
