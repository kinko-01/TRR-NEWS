from datetime import datetime, timezone
from flask_login import UserMixin
from sqlalchemy import CheckConstraint
from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "user"
    __table_args__ = (CheckConstraint("role IN ('reader', 'journalist', 'editor', 'admin')", name="ck_user_role"),)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255))
    google_id = db.Column(db.String(255), unique=True, nullable=True)
    profile_image = db.Column(db.String(500))
    role = db.Column(db.String(30), default="reader", nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    articles = db.relationship("Article", backref="author", lazy=True)
