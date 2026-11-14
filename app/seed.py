from datetime import datetime, timezone

from app.extensions import db
from .models import Article, Category, User


DEFAULT_CATEGORIES = [
    ("Politics", "politics"),
    ("Business", "business"),
    ("Technology", "technology"),
    ("Sports", "sports"),
    ("Entertainment", "entertainment"),
    ("Health", "health"),
    ("Education", "education"),
    ("World", "world"),
    ("Opinion", "opinion"),
]


def seed_database(sample_content=False):
    changed = False
    for name, slug in DEFAULT_CATEGORIES:
        if not Category.query.filter_by(slug=slug).first():
            db.session.add(Category(name=name, slug=slug))
            changed = True
    if changed:
        db.session.commit()

    if sample_content and Article.query.count() == 0:
        admin = User.query.filter_by(role="admin", is_active=True).first()
        category = Category.query.filter_by(slug="technology").first()
        if admin and category:
            db.session.add(
                Article(
                    title="Welcome to TRR NEWS",
                    slug="welcome-to-trr-news",
                    excerpt="Your home for timely stories, analysis, business, technology, sports and more.",
                    content="<p>Welcome to TRR NEWS. This sample article demonstrates the publishing system.</p>",
                    author_id=admin.id,
                    category_id=category.id,
                    status="published",
                    is_featured=True,
                    published_at=datetime.now(timezone.utc),
                )
            )
            db.session.commit()
