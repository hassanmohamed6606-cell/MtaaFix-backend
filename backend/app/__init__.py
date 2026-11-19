
from flask import Flask, jsonify, render_template_string, send_from_directory
from pathlib import Path
from flask_cors import CORS
from app.config import Config
from app.extensions import db, jwt, migrate
from app.models import Report, User  # noqa: F401 - register models
from app.routes import auth_bp, reports_bp


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)

    if test_config:
        app.config.update(test_config)

    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": app.config["FRONTEND_ORIGIN"]
            }
        }
    )

    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(auth_bp)
    app.register_blueprint(reports_bp)

    # Swagger: serve OpenAPI specification
    @app.get("/openapi.yaml")
    def openapi_spec():
        docs_folder = Path(app.root_path).parent / "docs"
        return send_from_directory(
            str(docs_folder),
            "openapi.yaml",
            mimetype="application/yaml"
        )

    # Swagger: interactive API documentation
    @app.get("/docs")
    def swagger_docs():
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>MtaaFix API Documentation</title>
            <link rel="stylesheet"
                  href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
        </head>
        <body>
            <div id="swagger-ui"></div>
            <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>

            <script>
                window.onload = function() {
                    SwaggerUIBundle({
                        url: "/openapi.yaml",
                        dom_id: "#swagger-ui",
                        persistAuthorization: true
                    });
                };
            </script>
        </body>
        </html>
        """)

    # API health check
    @app.get("/api/health")
    def health():
        return jsonify(
            status="ok",
            message="MtaaFix API is running."
        )

    # Database health and engine diagnostic
    @app.get("/api/db-health")
    def db_health():
        from sqlalchemy import text

        try:
            db.session.execute(text("SELECT 1"))

            return jsonify(
                status="ok",
                database="connected",
                dialect=db.engine.dialect.name,
                driver=db.engine.dialect.driver
                database_url_present=bool(os.getenv("DATABASE_URL")),
                configured_database=app.config["SQLALCHEMY_DATABASE_URI"].split(":")[0]
            ), 200

        except Exception:
            app.logger.exception("Database connection test failed")
            db.session.rollback()

            return jsonify(
                status="error",
                database="unavailable"
            ), 503

    # Handle oversized uploads
    @app.errorhandler(413)
    def too_large(_error):
        return jsonify(
            error="Image is too large. Maximum upload size is 8 MB."
        ), 413

    # Create database tables if enabled
    if app.config.get("AUTO_CREATE_DB"):
        with app.app_context():
            db.create_all()

    return app
