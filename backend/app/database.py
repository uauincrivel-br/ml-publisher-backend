import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# DATABASE URL (prioriza ambiente, fallback só para DEV)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://mlpublisher:2Kp405zIs9umjdTeJzJTI8pM9kw9fN86@dpg-d8tldsf7f7vs73f8n0bg-a.oregon-postgres.render.com/mlpublisher"
)

# engine único centralizado
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    future=True
)

# sessão
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True
)

# BASE ÚNICA DO PROJETO (ALEMBIC USA ISSO)
Base = declarative_base()