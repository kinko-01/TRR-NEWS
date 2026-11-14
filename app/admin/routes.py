from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
import re
import uuid

import bleach
from PIL import Image, UnidentifiedImageError
from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Article, Category, Comment, User

admin_bp = Blueprint("admin", __name__)

ALLOWED_ROLES = {"reader", "journalist", "editor", "admin"}
ALLOWED_STATUSES = {"draft", "published"}
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
ALLOWED_IMAGE_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
ALLOWED_HTML_TAGS = {
    "p", "br", "strong", "em", "u", "blockquote", "ul", "ol", "li", "h2", "h3", "a"
}
ALLOWED_HTML_ATTRIBUTES = {"a": ["href", "title", "target", "rel"]}


def slugify(value):
    value = re.sub(r"[^a-zA-Z0-9\s-]", "", value).strip().lower()
    return re.sub(r"[-\s]+", "-", value)


def sanitize_content(value):
    return bleach.clean(
        value or "",
        tags=ALLOWED_HTML_TAGS,
        attributes=ALLOWED_HTML_ATTRIBUTES,
        protocols={"http", "https", "mailto"},
        strip=True,
    )


def unique_article_slug(title, article_id=None):
    base = slugify(title)[:250] or "article"
    slug = base
    counter = 2
    while True:
        query = Article.query.filter_by(slug=slug)
        if article_id:
            query = query.filter(Article.id != article_id)
        if not query.first():
            return slug
        slug = f"{base[:(280 - len(str(counter)) - 1)]}-{counter}"
        counter += 1


def unique_category_slug(name):
    base = slugify(name)[:90] or "category"
    slug = base
    counter = 2
    while Category.query.filter_by(slug=slug).first():
        slug = f"{base[:(100 - len(str(counter)) - 1)]}-{counter}"
        counter += 1
    return slug


def newsroom_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.role not in {"admin", "editor", "journalist"}:
            flash("You do not have access to the newsroom dashboard.", "danger")
            return redirect(url_for("main.home"))
        return view(*args, **kwargs)
    return wrapped


def editor_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.role not in {"admin", "editor"}:
            flash("Editor permission required.", "danger")
            return redirect(url_for("admin.dashboard"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.role != "admin":
            flash("Administrator permission required.", "danger")
            return redirect(url_for("admin.dashboard"))
        return view(*args, **kwargs)
    return wrapped


def can_edit_article(article):
    return current_user.role in {"admin", "editor"} or article.author_id == current_user.id


def save_image(upload):
    if current_app.config.get("VERCEL_RUNTIME"):
        if upload and upload.filename:
            raise ValueError("Image uploads are disabled in this Vercel test build. Add external image storage before enabling uploads.")
        return None
    if not upload or not upload.filename:
        return None

    original = secure_filename(upload.filename)
    suffix = Path(original).suffix.lower().lstrip(".")
    if suffix not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("Only JPG, PNG and WebP images are allowed.")

    try:
        upload.stream.seek(0)
        image = Image.open(upload.stream)
        image.verify()
        upload.stream.seek(0)
        with Image.open(upload.stream) as checked:
            if checked.format not in ALLOWED_IMAGE_FORMATS:
                raise ValueError("Unsupported image format.")
            if checked.width * checked.height > current_app.config["MAX_IMAGE_PIXELS"]:
                raise ValueError("The image dimensions are too large.")
            safe_ext = ALLOWED_IMAGE_FORMATS[checked.format]
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("The uploaded file is not a valid image.") from exc

    filename = f"{uuid.uuid4().hex}.{safe_ext}"
    destination = Path(current_app.config["UPLOAD_FOLDER"]) / filename
    upload.stream.seek(0)
    with destination.open("wb") as output:
        output.write(upload.stream.read())
    return filename


def delete_image(filename):
    if not filename:
        return
    path = (Path(current_app.config["UPLOAD_FOLDER"]) / filename).resolve()
    upload_dir = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    if upload_dir in path.parents and path.is_file():
        path.unlink(missing_ok=True)


@admin_bp.route("/")
@newsroom_required
def dashboard():
    return render_template(
        "admin/dashboard.html",
        articles=Article.query.count(),
        published=Article.query.filter_by(status="published").count(),
        drafts=Article.query.filter_by(status="draft").count(),
        views=db.session.query(db.func.coalesce(db.func.sum(Article.views), 0)).scalar(),
        comments=Comment.query.filter_by(is_approved=False).count(),
    )


@admin_bp.route("/articles")
@newsroom_required
def articles():
    query = Article.query
    if current_user.role == "journalist":
        query = query.filter_by(author_id=current_user.id)
    return render_template("admin/articles.html", articles=query.order_by(Article.created_at.desc()).all())


@admin_bp.route("/articles/new", methods=["GET", "POST"])
@newsroom_required
def new_article():
    categories = Category.query.order_by(Category.name).all()
    if not categories:
        flash("Create a category before creating an article.", "warning")
        return redirect(url_for("admin.categories"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        excerpt = request.form.get("excerpt", "").strip()
        content = sanitize_content(request.form.get("content", "").strip())
        category_id = request.form.get("category_id", "").strip()
        requested_status = request.form.get("status", "draft")

        if not title or not content or not category_id:
            flash("Title, category and content are required.", "danger")
            return render_template("admin/article_form.html", article=None, categories=categories)
        if len(title) > 250 or len(excerpt) > 2000:
            flash("The headline or excerpt is too long.", "danger")
            return render_template("admin/article_form.html", article=None, categories=categories)
        try:
            category_id = int(category_id)
        except ValueError:
            flash("Invalid category.", "danger")
            return render_template("admin/article_form.html", article=None, categories=categories)
        if not db.session.get(Category, category_id):
            flash("The selected category does not exist.", "danger")
            return render_template("admin/article_form.html", article=None, categories=categories)

        status = requested_status if requested_status in ALLOWED_STATUSES else "draft"
        if current_user.role == "journalist":
            status = "draft"

        filename = None
        try:
            filename = save_image(request.files.get("featured_image"))
            article = Article(
                title=title,
                slug=unique_article_slug(title),
                excerpt=excerpt,
                content=content,
                category_id=category_id,
                author_id=current_user.id,
                status=status,
                is_breaking=bool(request.form.get("is_breaking")) if status == "published" else False,
                is_featured=bool(request.form.get("is_featured")) if status == "published" else False,
                featured_image=filename,
                published_at=datetime.now(timezone.utc) if status == "published" else None,
            )
            db.session.add(article)
            db.session.commit()
        except ValueError as exc:
            db.session.rollback()
            delete_image(filename)
            flash(str(exc), "danger")
            return render_template("admin/article_form.html", article=None, categories=categories)
        except Exception:
            db.session.rollback()
            delete_image(filename)
            current_app.logger.exception("Article creation failed")
            flash("The article could not be saved.", "danger")
            return render_template("admin/article_form.html", article=None, categories=categories)

        flash("Article saved.", "success")
        return redirect(url_for("admin.articles"))
    return render_template("admin/article_form.html", article=None, categories=categories)


@admin_bp.route("/articles/<int:article_id>/edit", methods=["GET", "POST"])
@newsroom_required
def edit_article(article_id):
    article = Article.query.get_or_404(article_id)
    if not can_edit_article(article):
        flash("You can only edit your own articles.", "danger")
        return redirect(url_for("admin.articles"))

    categories = Category.query.order_by(Category.name).all()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        excerpt = request.form.get("excerpt", "").strip()
        content = sanitize_content(request.form.get("content", "").strip())
        category_id = request.form.get("category_id", "").strip()
        requested_status = request.form.get("status", "draft")

        try:
            category_id = int(category_id)
        except ValueError:
            flash("Invalid category.", "danger")
            return render_template("admin/article_form.html", article=article, categories=categories)

        if not title or not content or not db.session.get(Category, category_id):
            flash("A valid headline, category and article body are required.", "danger")
            return render_template("admin/article_form.html", article=article, categories=categories)

        status = requested_status if requested_status in ALLOWED_STATUSES else article.status
        if current_user.role == "journalist" and status == "published" and article.status != "published":
            status = "draft"

        old_image = article.featured_image
        new_image = None
        try:
            article.title = title
            article.excerpt = excerpt[:2000]
            article.content = content
            article.category_id = category_id
            article.status = status
            article.is_breaking = bool(request.form.get("is_breaking")) if status == "published" and current_user.role in {"admin", "editor"} else False
            article.is_featured = bool(request.form.get("is_featured")) if status == "published" and current_user.role in {"admin", "editor"} else False
            if status == "published" and not article.published_at:
                article.published_at = datetime.now(timezone.utc)
            elif status == "draft":
                article.published_at = None

            image = request.files.get("featured_image")
            if image and image.filename:
                new_image = save_image(image)
                article.featured_image = new_image

            db.session.commit()
            if new_image and old_image:
                delete_image(old_image)
        except ValueError as exc:
            db.session.rollback()
            delete_image(new_image)
            flash(str(exc), "danger")
            return render_template("admin/article_form.html", article=article, categories=categories)
        except Exception:
            db.session.rollback()
            delete_image(new_image)
            current_app.logger.exception("Article update failed")
            flash("The article could not be updated.", "danger")
            return render_template("admin/article_form.html", article=article, categories=categories)

        flash("Article updated.", "success")
        return redirect(url_for("admin.articles"))
    return render_template("admin/article_form.html", article=article, categories=categories)


@admin_bp.route("/articles/<int:article_id>/delete", methods=["POST"])
@editor_required
def delete_article(article_id):
    article = Article.query.get_or_404(article_id)
    image = article.featured_image
    db.session.delete(article)
    db.session.commit()
    delete_image(image)
    flash("Article deleted.", "success")
    return redirect(url_for("admin.articles"))


@admin_bp.route("/categories", methods=["GET", "POST"])
@editor_required
def categories():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        if not 2 <= len(name) <= 80:
            flash("Category name must be between 2 and 80 characters.", "danger")
        else:
            slug = unique_category_slug(name)
            if Category.query.filter(db.func.lower(Category.name) == name.lower()).first():
                flash("That category already exists.", "warning")
            else:
                try:
                    db.session.add(Category(name=name, slug=slug, description=description[:500] or None))
                    db.session.commit()
                    flash("Category added.", "success")
                except IntegrityError:
                    db.session.rollback()
                    flash("That category could not be created.", "danger")
    return render_template("admin/categories.html", categories=Category.query.order_by(Category.name).all())


@admin_bp.route("/comments")
@editor_required
def comments():
    return render_template("admin/comments.html", comments=Comment.query.order_by(Comment.created_at.desc()).all())


@admin_bp.route("/comments/<int:comment_id>/approve", methods=["POST"])
@editor_required
def approve_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    comment.is_approved = True
    db.session.commit()
    flash("Comment approved.", "success")
    return redirect(url_for("admin.comments"))


@admin_bp.route("/comments/<int:comment_id>/delete", methods=["POST"])
@editor_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    db.session.delete(comment)
    db.session.commit()
    flash("Comment deleted.", "success")
    return redirect(url_for("admin.comments"))


@admin_bp.route("/users")
@admin_required
def users():
    return render_template("admin/users.html", users=User.query.order_by(User.created_at.desc()).all())


@admin_bp.route("/users/<int:user_id>/role", methods=["POST"])
@admin_required
def change_role(user_id):
    user = User.query.get_or_404(user_id)
    role = request.form.get("role")
    if role not in ALLOWED_ROLES:
        flash("Invalid role.", "danger")
        return redirect(url_for("admin.users"))
    if user.id == current_user.id and role != "admin":
        flash("You cannot remove your own administrator access.", "danger")
        return redirect(url_for("admin.users"))
    if user.role == "admin" and role != "admin" and User.query.filter_by(role="admin", is_active=True).count() <= 1:
        flash("The last active administrator cannot be demoted.", "danger")
        return redirect(url_for("admin.users"))
    user.role = role
    db.session.commit()
    flash(f"{user.name}'s role was updated.", "success")
    return redirect(url_for("admin.users"))
