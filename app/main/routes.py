from html import escape
from email.utils import format_datetime
from datetime import timezone
from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import or_
from app.extensions import db, limiter
from app.models import Article, Category, Comment


main_bp = Blueprint("main", __name__)


def published_query():
    return Article.query.filter(Article.status == "published", Article.published_at.is_not(None))


@main_bp.route("/")
def home():
    featured = published_query().filter_by(is_featured=True).order_by(Article.published_at.desc()).first()
    breaking = published_query().filter_by(is_breaking=True).order_by(Article.published_at.desc()).limit(8).all()
    page = request.args.get("page", 1, type=int)
    latest_pagination = published_query().order_by(Article.published_at.desc()).paginate(page=page, per_page=12, error_out=False)
    latest = latest_pagination.items
    most_read = published_query().order_by(Article.views.desc()).limit(5).all()
    categories = Category.query.order_by(Category.name).all()
    return render_template("index.html", featured=featured, breaking=breaking, latest=latest, latest_pagination=latest_pagination, most_read=most_read, categories=categories)


@main_bp.route("/article/<slug>", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"]) if limiter else (lambda view: view)
def article(slug):
    article = published_query().filter_by(slug=slug).first_or_404()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        content = request.form.get("content", "").strip()
        if not 2 <= len(name) <= 120 or len(content) < 2 or len(content) > 5000:
            flash("Please provide a valid name and a comment between 2 and 5000 characters.", "danger")
        elif email and ("@" not in email or len(email) > 255):
            flash("Please provide a valid email address.", "danger")
        else:
            db.session.add(Comment(article_id=article.id, name=name, email=email or None, content=content, is_approved=False))
            db.session.commit()
            flash("Your comment was submitted for moderation.", "success")
            return redirect(url_for("main.article", slug=article.slug) + "#comments")

    article.views = (article.views or 0) + 1
    db.session.commit()
    approved_comments = Comment.query.filter_by(article_id=article.id, is_approved=True).order_by(Comment.created_at.asc()).all()
    related = published_query().filter(Article.category_id == article.category_id, Article.id != article.id).order_by(Article.published_at.desc()).limit(3).all()
    return render_template("article.html", article=article, comments=approved_comments, related=related)


@main_bp.route("/category/<slug>")
def category(slug):
    category = Category.query.filter_by(slug=slug).first_or_404()
    page = request.args.get("page", 1, type=int)
    articles = published_query().filter_by(category_id=category.id).order_by(Article.published_at.desc()).paginate(page=page, per_page=12, error_out=False)
    return render_template("category.html", category=category, articles=articles)


@main_bp.route("/search")
def search():
    q = request.args.get("q", "").strip()[:120]
    articles = None
    if q:
        pattern = f"%{q}%"
        articles = published_query().filter(
            or_(Article.title.ilike(pattern), Article.excerpt.ilike(pattern), Article.content.ilike(pattern))
        ).order_by(Article.published_at.desc()).paginate(page=request.args.get("page", 1, type=int), per_page=12, error_out=False)
    return render_template("search.html", q=q, articles=articles)


@main_bp.route("/about")
def about():
    return render_template("about.html")


@main_bp.route("/robots.txt")
def robots():
    return Response(
        f"User-agent: *\nAllow: /\nDisallow: /admin/\nDisallow: /auth/\nSitemap: {url_for('main.sitemap', _external=True)}\n",
        mimetype="text/plain",
    )


@main_bp.route("/feed.xml")
def rss_feed():
    """RSS 2.0 feed for readers and news aggregators."""
    articles = published_query().order_by(Article.published_at.desc()).limit(30).all()
    items = []
    for article in articles:
        link = url_for("main.article", slug=article.slug, _external=True)
        pubdate = format_datetime(article.published_at if article.published_at.tzinfo else article.published_at.replace(tzinfo=timezone.utc))
        title = escape(article.title)
        description = escape(article.excerpt or article.content[:300])
        items.append(f"<item><title>{title}</title><link>{escape(link)}</link><guid>{escape(link)}</guid><description>{description}</description><pubDate>{pubdate}</pubDate></item>")
    channel_link = escape(url_for("main.home", _external=True))
    xml = '<?xml version="1.0" encoding="UTF-8"?>' + f'<rss version="2.0"><channel><title>TRR NEWS</title><link>{channel_link}</link><description>Latest reporting and stories from TRR NEWS</description>{"".join(items)}</channel></rss>'
    return Response(xml, mimetype="application/rss+xml; charset=utf-8")


@main_bp.route("/sitemap.xml")
def sitemap():
    articles = published_query().order_by(Article.published_at.desc()).all()
    categories = Category.query.order_by(Category.slug).all()
    urls = [(url_for("main.home", _external=True), None), (url_for("main.about", _external=True), None)]
    urls += [(url_for("main.article", slug=a.slug, _external=True), a.published_at) for a in articles]
    urls += [(url_for("main.category", slug=c.slug, _external=True), c.created_at) for c in categories]
    parts = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for location, lastmod in urls:
        parts.append("<url><loc>{}</loc>{}</url>".format(escape(location), f"<lastmod>{lastmod.isoformat()}</lastmod>" if lastmod else ""))
    parts.append("</urlset>")
    return Response("".join(parts), mimetype="application/xml")
