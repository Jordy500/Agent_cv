import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def get_database_url() -> str:
    # Default to a local SQLite DB in project root
    default_path = Path(__file__).parent.parent / "agent.db"
    return os.getenv("DATABASE_URL", f"sqlite:///{default_path}")


DATABASE_URL = get_database_url()
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_session():
    return SessionLocal()
