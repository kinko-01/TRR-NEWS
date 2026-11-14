from app.extensions import db
from app.models import Article, User


def login(client, email="admin@example.com", password="AdminPassword123!"):
    response = client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=False)
    assert response.status_code == 302
    return response


def test_public_pages_and_health(client):
    for path in ["/", "/about", "/search?q=news", "/robots.txt", "/sitemap.xml", "/healthz"]:
        response = client.get(path)
        assert response.status_code == 200


def test_csrf_blocks_missing_token_when_enabled(app, client):
    app.config["WTF_CSRF_ENABLED"] = True
    response = client.post("/auth/login", data={"email": "admin@example.com", "password": "AdminPassword123!"})
    assert response.status_code == 400


def test_login_and_newsroom_access(client):
    login(client)
    response = client.get("/admin/")
    assert response.status_code == 200
    assert b"Newsroom Dashboard" in response.data


def test_reader_cannot_access_newsroom(app, client):
    with app.app_context():
        from werkzeug.security import generate_password_hash
        db.session.add(User(name="Reader", email="reader@example.com", password_hash=generate_password_hash("ReaderPassword123!"), role="reader", is_active=True))
        db.session.commit()
    login(client, "reader@example.com", "ReaderPassword123!")
    assert client.get("/admin/").status_code == 302


def test_article_creation_and_public_visibility(app, client):
    login(client)
    response = client.get("/admin/articles/new")
    assert response.status_code == 200
    with client.session_transaction() as session:
        pass

    # Extract CSRF token from the form rendered after login.
    import re
    page = client.get("/admin/articles/new")
    token = re.search(rb'name="csrf_token" value="([^"]+)"', page.data).group(1).decode()
    response = client.post(
        "/admin/articles/new",
        data={
            "csrf_token": token,
            "title": "Test Story",
            "excerpt": "A test story.",
            "category_id": "1",
            "content": "<p>Hello <script>alert(1)</script></p>",
            "status": "published",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    with app.app_context():
        article = Article.query.filter_by(slug="test-story").first()
        assert article is not None
        assert "script" not in article.content


def test_rss_feed_and_pagination_routes(client):
    assert client.get("/feed.xml").status_code == 200
    assert b"<rss" in client.get("/feed.xml").data
    assert client.get("/?page=1").status_code == 200
    assert client.get("/category/technology?page=1").status_code == 200


def test_google_auth_is_disabled(client):
    response = client.get("/auth/google", follow_redirects=False)
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]
