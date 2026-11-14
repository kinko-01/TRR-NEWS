from datetime import datetime, timezone
from app.extensions import db


class Comment(db.Model):
    __tablename__ = "comment"
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey("article.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255))
    content = db.Column(db.Text, nullable=False)
    is_approved = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
