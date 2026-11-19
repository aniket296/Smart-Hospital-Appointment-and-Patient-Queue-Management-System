"""Flask application factory."""

import os
from flask import Flask
from backend.app.config import CONFIG_BY_NAME, Config
from backend.app.extensions import cors, db
from backend.app.routes.appointments import appointments_bp
from backend.app.routes.auth import auth_bp
from backend.app.routes.health import health_bp
from backend.app.routes.master import master_bp
from backend.app.routes.notifications import notifications_bp
from backend.app.routes.reports import reports_bp
from backend.app.utils.errors import register_error_handlers


def create_app(config_name: str | None = None, config_overrides: dict | None = None) -> Flask:
    """Create and configure the Flask application instance."""
    app = Flask(__name__)

    env_name = config_name or os.getenv("FLASK_ENV", "development")
    config_class = CONFIG_BY_NAME.get(env_name, Config)
    app.config.from_object(config_class)

    if config_overrides:
        app.config.update(config_overrides)

    db.init_app(app)
    cors_origins = app.config.get("CORS_ORIGINS", "*")
    cors.init_app(app, resources={r"/api/*": {"origins": cors_origins}})

    # Import models so SQLAlchemy metadata is registered
    from backend.app import models  # noqa: F401

    register_error_handlers(app)

    # Register blueprints
    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(master_bp, url_prefix="/api")
    app.register_blueprint(appointments_bp, url_prefix="/api")
    app.register_blueprint(notifications_bp, url_prefix="/api")
    app.register_blueprint(reports_bp, url_prefix="/api")

    return app
