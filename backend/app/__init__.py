from flask import Flask, jsonify
from flask_cors import CORS
from app.config import Config
from app.extensions import db, jwt, migrate
from app.models import Report, User  # noqa: F401 - register models with SQLAlchemy
from app.routes import auth_bp, reports_bp


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    CORS(app, resources={r"/api/*": {"origins": app.config["FRONTEND_ORIGIN"]}})
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    app.register_blueprint(auth_bp)
    app.register_blueprint(reports_bp)

    @app.get("/api/health")
    def health():
        return jsonify(status="ok", message="MtaaFix API is running.")

    @app.errorhandler(413)
    def too_large(_error):
        return jsonify(error="Image is too large. Maximum upload size is 8 MB."), 413

    if app.config.get("AUTO_CREATE_DB"):
        with app.app_context():
            db.create_all()
    return app
