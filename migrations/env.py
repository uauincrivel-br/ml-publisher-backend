from logging.config import fileConfig
import os
import sys

from alembic import context
from sqlalchemy import create_engine, pool

# =========================================================
# PATH DO PROJETO
# =========================================================
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.append(BASE_DIR)

# =========================================================
# IMPORTS CORRETOS PARA ALEMBIC AUTOGENERATE
# =========================================================
from backend.app.database import Base
from backend.app.models import models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# =========================================================
# METADATA PARA AUTOGENERATE
# =========================================================
target_metadata = Base.metadata


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        return database_url

    alembic_url = config.get_main_option("sqlalchemy.url")

    if not alembic_url:
        raise RuntimeError(
            "DATABASE_URL não definida e sqlalchemy.url ausente no alembic.ini"
        )

    return alembic_url


# =========================================================
# OFFLINE MIGRATION
# =========================================================
def run_migrations_offline() -> None:
    url = get_database_url()

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# =========================================================
# ONLINE MIGRATION
# =========================================================
def run_migrations_online() -> None:
    connectable = create_engine(
        get_database_url(),
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# =========================================================
# EXECUTION MODE
# =========================================================
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
