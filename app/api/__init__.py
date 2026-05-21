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
