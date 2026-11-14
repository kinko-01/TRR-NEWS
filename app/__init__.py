import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, jsonify, render_template
from flask_wtf.csrf import CSRFError
from werkzeug.middleware.proxy_fix import ProxyFix
from markupsafe import Markup
import bleach

from config import Config, DevelopmentConfig, ProductionConfig, TestingConfig
from .extensions import db, login_manager, csrf, limiter


try:
    from flask_migrate import Migrate
except ImportError:
    Migrate = None


def create_app(config_object=None):
    app = Flask(__name__, instance_relative_config=True)
    config_object = config_object or os.getenv("FLASK_CONFIG", "development").lower()
    config_map = {"development": DevelopmentConfig, "testing": TestingConfig, "production": ProductionConfig}
    if isinstance(config_object, str):
        config_object = config_map.get(config_object, Config)
    app.config.from_object(config_object)

    # Vercel functions need a managed database; their local filesystem is not durable.
    if config_object is ProductionConfig and os.getenv("VERCEL") and not os.getenv("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL must be configured in Vercel Project Environment Variables.")

    if not app.config.get("SECRET_KEY"):
        if app.config.get("TESTING"):
            app.config["SECRET_KEY"] = "testing-only-secret"
        else:
            raise RuntimeError("SECRET_KEY must be set in the environment.")

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    if Migrate is not None:
        Migrate(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    if limiter is not None:
        limiter.init_app(app)

    from .models import User, Category

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    @app.template_filter("reading_time")
    def reading_time(value):
        words = len((value or "").split())
        return max(1, (words + 199) // 200)

    @app.template_filter("safe_html")
    def safe_html(value):
        allowed_tags = {"p", "br", "strong", "em", "u", "blockquote", "ul", "ol", "li", "h2", "h3", "a"}
        allowed_attributes = {"a": ["href", "title", "target", "rel"]}
        return Markup(bleach.clean(value or "", tags=allowed_tags, attributes=allowed_attributes, protocols={"http", "https", "mailto"}, strip=True))

    @app.context_processor
    def inject_globals():
        return {
            "site_name": app.config["TRR_SITE_NAME"],
            "site_url": app.config["TRR_SITE_URL"],
            "current_year": datetime.now(timezone.utc).year,
            "nav_categories": Category.query.order_by(Category.name.asc()).all(),
        }

    from .main.routes import main_bp
    from .auth.routes import auth_bp
    from .admin.routes import admin_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    @app.cli.command("create-admin")
    def create_admin_command():
        """Create the first administrator interactively."""
        import click
        from werkzeug.security import generate_password_hash
        email = click.prompt("Admin email", type=str).strip().lower()
        name = click.prompt("Admin name", type=str).strip()
        password = click.prompt("Admin password", hide_input=True, confirmation_prompt=True)
        if len(password) < 12:
            raise click.ClickException("Admin passwords must contain at least 12 characters.")
        if User.query.filter_by(email=email).first():
            raise click.ClickException("A user with that email already exists.")
        user = User(name=name[:120], email=email[:255], password_hash=generate_password_hash(password), role="admin", is_active=True)
        db.session.add(user)
        db.session.commit()
        click.echo("Administrator created successfully.")

    @app.cli.command("reset-admin")
    def reset_admin_command():
        """Reset an existing administrator password without exposing it in shell history."""
        import click
        from werkzeug.security import generate_password_hash
        email = click.prompt("Existing administrator email").strip().lower()
        user = User.query.filter_by(email=email).first()
        if user is None:
            raise click.ClickException("No account exists with that email. Check the address and try again.")
        password = click.prompt("New password (minimum 12 characters)", hide_input=True, confirmation_prompt=True)
        if len(password) < 12:
            raise click.ClickException("Administrator passwords must contain at least 12 characters.")
        user.password_hash = generate_password_hash(password)
        user.role = "admin"
        user.is_active = True
        db.session.commit()
        click.echo("Administrator password reset successfully. Sign in with the email you entered.")

    @app.cli.command("seed")
    def seed_command():
        """Seed the standard TRR NEWS categories."""
        import click
        from .seed import seed_database
        seed_database(sample_content=False)
        click.echo("Seed data applied.")

    @app.get("/healthz")
    def healthz():
        try:
            db.session.execute(db.text("SELECT 1"))
            return jsonify(status="ok", service="trr-news"), 200
        except Exception:
            app.logger.exception("Health check database failure")
            return jsonify(status="error", service="trr-news"), 503

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(413)
    def too_large(e):
        return render_template("error.html", message="The uploaded file is too large."), 413

    @app.errorhandler(CSRFError)
    def csrf_error(e):
        return render_template("error.html", message="Your session or form token is invalid. Please refresh and try again."), 400

    @app.errorhandler(400)
    def bad_request(e):
        return render_template("error.html", message="The request could not be processed."), 400

    @app.errorhandler(429)
    def too_many_requests(e):
        return render_template("error.html", message="Too many requests. Please try again later."), 429

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        app.logger.exception("Unhandled server error")
        return render_template("error.html", message="Something went wrong on the server."), 500

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; frame-ancestors 'self'; base-uri 'self'; form-action 'self'",
        )
        if app.config.get("SESSION_COOKIE_SECURE"):
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response

    if not app.debug:
        logging.basicConfig(level=logging.INFO)

    with app.app_context():
        if app.config.get("AUTO_CREATE_DB"):
            db.create_all()
            from .seed import seed_database
            seed_database(sample_content=app.config.get("SEED_SAMPLE_CONTENT", False))

    return app
