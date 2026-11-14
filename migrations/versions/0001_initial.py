"""Initial TRR NEWS schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-08
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("google_id", sa.String(length=255), nullable=True),
        sa.Column("profile_image", sa.String(length=500), nullable=True),
        sa.Column("role", sa.String(length=30), nullable=False, server_default="reader"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("google_id"),
        sa.CheckConstraint("role IN ('reader', 'journalist', 'editor', 'admin')", name="ck_user_role"),
    )
    op.create_index("ix_user_email", "user", ["email"], unique=True)

    op.create_table(
        "category",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_category_slug", "category", ["slug"], unique=True)

    op.create_table(
        "article",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=250), nullable=False),
        sa.Column("slug", sa.String(length=280), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("featured_image", sa.String(length=500), nullable=True),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("is_breaking", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("views", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["author_id"], ["user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["category_id"], ["category.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("slug"),
        sa.CheckConstraint("status IN ('draft', 'published')", name="ck_article_status"),
    )
    op.create_index("ix_article_slug", "article", ["slug"], unique=True)
    op.create_index("ix_article_author_id", "article", ["author_id"], unique=False)
    op.create_index("ix_article_category_id", "article", ["category_id"], unique=False)
    op.create_index("ix_article_status", "article", ["status"], unique=False)
    op.create_index("ix_article_is_breaking", "article", ["is_breaking"], unique=False)
    op.create_index("ix_article_is_featured", "article", ["is_featured"], unique=False)
    op.create_index("ix_article_published_at", "article", ["published_at"], unique=False)

    op.create_table(
        "comment",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_approved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["article_id"], ["article.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_comment_article_id", "comment", ["article_id"], unique=False)
    op.create_index("ix_comment_is_approved", "comment", ["is_approved"], unique=False)


def downgrade():
    op.drop_table("comment")
    op.drop_table("article")
    op.drop_table("category")
    op.drop_table("user")
