"""Flask application factory and WSGI entry point."""

import os
import sys
from pathlib import Path

# Allow importing both as `backend.app` (from repo root) and `app` (when rootDir is `backend` on Render)
_REPO_ROOT = str(Path(__file__).resolve().parents[2])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from flask import Flask
from backend.app.config import CONFIG_BY_NAME, Config, normalize_database_url, parse_cors_origins
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
    flask_app = Flask(__name__)

    env_name = config_name or os.getenv("FLASK_ENV", "development")
    config_class = CONFIG_BY_NAME.get(env_name, Config)
    flask_app.config.from_object(config_class)

    # Re-evaluate DATABASE_URL and CORS_ORIGINS dynamically if set in environment
    env_db_url = normalize_database_url(os.getenv("DATABASE_URL"))
    if env_db_url and env_name != "testing":
        flask_app.config["SQLALCHEMY_DATABASE_URI"] = env_db_url

    if os.getenv("CORS_ORIGINS") is not None:
        flask_app.config["CORS_ORIGINS"] = parse_cors_origins(os.getenv("CORS_ORIGINS"))

    if config_overrides:
        if "SQLALCHEMY_DATABASE_URI" in config_overrides:
            config_overrides = dict(config_overrides)
            config_overrides["SQLALCHEMY_DATABASE_URI"] = (
                normalize_database_url(config_overrides["SQLALCHEMY_DATABASE_URI"])
                or config_overrides["SQLALCHEMY_DATABASE_URI"]
            )
        flask_app.config.update(config_overrides)

    db.init_app(flask_app)
    cors_origins = flask_app.config.get("CORS_ORIGINS", "*")
    cors.init_app(flask_app, resources={r"/api/*": {"origins": cors_origins}})

    # Import models so SQLAlchemy metadata is registered
    from backend.app import models  # noqa: F401

    register_error_handlers(flask_app)

    # Register blueprints
    flask_app.register_blueprint(health_bp, url_prefix="/api")
    flask_app.register_blueprint(auth_bp, url_prefix="/api")
    flask_app.register_blueprint(master_bp, url_prefix="/api")
    flask_app.register_blueprint(appointments_bp, url_prefix="/api")
    flask_app.register_blueprint(notifications_bp, url_prefix="/api")
    flask_app.register_blueprint(reports_bp, url_prefix="/api")

    return flask_app


# Expose WSGI `app` instance so `gunicorn app:app --bind 0.0.0.0:$PORT` works inside `backend/`
app = create_app()
