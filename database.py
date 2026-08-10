import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# =====================================================
# URL PostgreSQL Railway
# =====================================================

DATABASE_URL = os.getenv("DATABASE_URL")


if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL est absente dans les variables Railway."
    )


# Railway peut donner postgres://
# SQLAlchemy utilise postgresql://

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql://",
        1
    )


# =====================================================
# Connexion PostgreSQL
# =====================================================

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)


# =====================================================
# Session SQLAlchemy
# =====================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# =====================================================
# Base des modèles
# =====================================================

Base = declarative_base()


# =====================================================
# Dépendance FastAPI
# =====================================================

def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()
