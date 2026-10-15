import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.config import Config

Base = declarative_base()

def init_postgres_db():
    """Attempt to create smartwaste_db database in PostgreSQL if it doesn't exist"""
    try:
        # Connect to default 'postgres' database to check/create target database
        root_uri = Config.get_postgres_uri(default_db="postgres")
        root_engine = create_engine(root_uri, isolation_level="AUTOCOMMIT")
        with root_engine.connect() as conn:
            result = conn.execute(
                text(f"SELECT 1 FROM pg_database WHERE datname = '{Config.PG_DATABASE}'")
            ).fetchone()
            if not result:
                conn.execute(text(f'CREATE DATABASE "{Config.PG_DATABASE}"'))
                print(f"[DB] Created PostgreSQL database: {Config.PG_DATABASE}")
            else:
                print(f"[DB] PostgreSQL database '{Config.PG_DATABASE}' already exists.")
        root_engine.dispose()
        return True
    except Exception as e:
        print(f"[DB Warning] Could not initialize PostgreSQL database: {e}")
        return False

def create_db_engine():
    """Tries PostgreSQL first; falls back gracefully to SQLite if needed."""
    if Config.DB_TYPE.lower() == "postgres":
        if init_postgres_db():
            try:
                pg_uri = Config.get_postgres_uri()
                engine = create_engine(pg_uri, pool_pre_ping=True)
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                print(f"[DB] Successfully connected to PostgreSQL at {Config.PG_HOST}:{Config.PG_PORT}/{Config.PG_DATABASE}")
                return engine, "postgres"
            except Exception as e:
                print(f"[DB Warning] PostgreSQL connection error: {e}")
                print("[DB] Falling back to SQLite local engine for seamless operation.")
        else:
            print("[DB] Falling back to SQLite local engine for seamless operation.")

    # SQLite Fallback / Standalone mode
    sqlite_uri = Config.get_sqlite_uri()
    engine = create_engine(sqlite_uri, connect_args={"check_same_thread": False})
    print(f"[DB] Connected to SQLite database at: {Config.SQLITE_PATH}")
    return engine, "sqlite"

engine, active_db_type = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
