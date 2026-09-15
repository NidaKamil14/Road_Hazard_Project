import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

# Locate and load .env from backend/ or project root
current_dir = Path(__file__).resolve().parent
env_backend = current_dir / ".env"
env_root = current_dir.parent / ".env"

if env_backend.exists():
    load_dotenv(dotenv_path=env_backend)
elif env_root.exists():
    load_dotenv(dotenv_path=env_root)
else:
    load_dotenv()

# Read database URL (defaults to standard local PostgreSQL port 5432 with psycopg driver)
DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/road_hazard_db"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

# Configure SQLAlchemy engine with pool_pre_ping to automatically recover stale connections
# Connect args with short connect_timeout for fast recovery if DB is offline
connect_args = {}
if "psycopg" in DATABASE_URL or "postgresql" in DATABASE_URL:
    connect_args = {"connect_timeout": 3}

try:
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        connect_args=connect_args,
    )
except Exception as e:
    import re
    masked_url = re.sub(r":([^@]+)@", ":***@", DATABASE_URL) if DATABASE_URL else "None"
    print(f"[Database Error] Could not initialize engine with URL '{masked_url}': {e}")
    # Fallback dummy engine if URL syntax is malformed
    engine = None

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI request dependency for database sessions."""
    if SessionLocal is None:
        raise RuntimeError("Database session maker is not configured.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_status() -> str:
    """Non-blocking database connectivity check for health monitoring.
    Returns:
        'connected' if the database is reachable and responds to SELECT 1.
        'disconnected' otherwise.
    """
    if engine is None:
        return "disconnected"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "connected"
    except Exception:
        return "disconnected"
