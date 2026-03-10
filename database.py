"""Database connection and session. Uses SQLite by default; set DATABASE_URL for Postgres."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

_url = os.environ.get("HANDOFF_DATABASE_URL", "")
DATABASE_URL = _url.strip() or "sqlite:///./handoff.db"
# SQLite needs check_same_thread=False for FastAPI
connect_args = {} if not DATABASE_URL.startswith("sqlite") else {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
