from logging.config import fileConfig

from alembic import context
from flask import Flask, current_app

from config import Config
from app.extensions import db

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Ensure models are imported before autogenerate/migrations run.
from app import models  # noqa: F401,E402

target_metadata = db.metadata


def get_url():
    return current_app.config["SQLALCHEMY_DATABASE_URI"]


def run_migrations_offline():
    context.configure(url=get_url(), target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    with db.engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


migration_app = Flask(__name__, instance_relative_config=True)
migration_app.config.from_object(Config)
db.init_app(migration_app)

with migration_app.app_context():
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()
