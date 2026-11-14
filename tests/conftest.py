import pytest
from app import create_app
from app.extensions import db
from app.models import Category, User
from werkzeug.security import generate_password_hash


@pytest.fixture()
def app():
    app = create_app("testing")
    with app.app_context():
        db.drop_all()
        db.create_all()
        db.session.add(Category(name="Technology", slug="technology"))
        db.session.add(User(name="Admin", email="admin@example.com", password_hash=generate_password_hash("AdminPassword123!"), role="admin", is_active=True))
        db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
