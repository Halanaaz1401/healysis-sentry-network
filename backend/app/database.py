import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings, BASE_DIR

Base = declarative_base()

def get_engine():
    """
    Creates and returns a SQLAlchemy Engine.
    Tries PostgreSQL first; if connection fails, gracefully falls back to local SQLite.
    When running under automated tests (TESTING=true or 'pytest' in modules), isolates into
    a separate healysis_test.db SQLite database so tests never wipe active dev data.
    """
    is_testing = (
        settings.TESTING 
        or os.getenv("TESTING", "").lower() == "true"
        or "pytest" in sys.modules
    )
    if is_testing:
        test_sqlite = f"sqlite:///{BASE_DIR}/healysis_test.db"
        return create_engine(
            test_sqlite,
            connect_args={"check_same_thread": False}
        )

    if settings.DATABASE_URL.startswith("postgresql"):
        try:
            pg_engine = create_engine(
                settings.DATABASE_URL,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20
            )
            with pg_engine.connect() as conn:
                pass
            return pg_engine
        except Exception:
            pass
            
    return create_engine(
        settings.SQLITE_FALLBACK_URL,
        connect_args={"check_same_thread": False}
    )

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
