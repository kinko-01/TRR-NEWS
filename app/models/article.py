from datetime import datetime, timezone
from sqlalchemy import CheckConstraint
from app.extensions import db


class Article(db.Model):
    __tablename__ = "article"
    __table_args__ = (CheckConstraint("status IN ('draft', 'published')", name="ck_article_status"),)
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), nullable=False)
    slug = db.Column(db.String(280), unique=True, nullable=False, index=True)
    excerpt = db.Column(db.Text)
    content = db.Column(db.Text, nullable=False)
    featured_image = db.Column(db.String(500))
    author_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="RESTRICT"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id", ondelete="RESTRICT"), nullable=False, index=True)
    status = db.Column(db.String(20), default="draft", nullable=False, index=True)
    is_breaking = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_featured = db.Column(db.Boolean, default=False, nullable=False, index=True)
    views = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    published_at = db.Column(db.DateTime(timezone=True), index=True)
    comments = db.relationship("Comment", backref="article", lazy=True, cascade="all, delete-orphan")
