from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, limiter
from app.models import User


auth_bp = Blueprint("auth", __name__)


def auth_redirect():
    if current_user.is_authenticated:
        if current_user.role in {"admin", "editor", "journalist"}:
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("main.home"))
    return None


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute") if limiter else (lambda view: view)
def login():
    response = auth_redirect()
    if response:
        return response
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and user.is_active and user.password_hash and check_password_hash(user.password_hash, password):
            login_user(user, remember=True)
            return redirect(url_for("admin.dashboard") if user.role in {"admin", "editor", "journalist"} else url_for("main.home"))
        flash("Invalid login details.", "danger")
    return render_template("auth/login.html")


@auth_bp.route("/signup", methods=["GET", "POST"])
@limiter.limit("5 per hour") if limiter else (lambda view: view)
def signup():
    response = auth_redirect()
    if response:
        return response
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not 2 <= len(name) <= 120:
            flash("Name must be between 2 and 120 characters.", "danger")
        elif "@" not in email or len(email) > 255:
            flash("Enter a valid email address.", "danger")
        elif len(password) < 8:
            flash("Password must contain at least 8 characters.", "danger")
        elif User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "warning")
        else:
            user = User(name=name, email=email, password_hash=generate_password_hash(password), role="reader")
            db.session.add(user)
            db.session.commit()
            login_user(user, remember=True)
            flash("Welcome to TRR NEWS!", "success")
            return redirect(url_for("main.home"))
    return render_template("auth/signup.html")


@auth_bp.route("/google")
def google_login():
    # Google authentication is intentionally disabled for this early release.
    flash("Google sign-in is temporarily disabled. Please use email and password.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/google/callback")
def google_callback():
    # Kept as a safe compatibility route so old bookmarks/Google callbacks do not break.
    flash("Google sign-in is temporarily disabled. Please use email and password.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    flash("You have been signed out.", "success")
    return redirect(url_for("main.home"))
