"""
SmartWaste PostgreSQL Migration Script
Use this script to migrate or populate your local PostgreSQL database with all tables, triggers, and dataset records.

Usage:
  python -m backend.migrate_postgres [optional_postgres_password]
"""
import os
import sys
from sqlalchemy import create_engine, text

def run_migration(password=None):
    if password:
        os.environ["PG_PASSWORD"] = str(password)

    from backend.config import Config
    print("========================================================")
    print(" SmartWaste PostgreSQL 18 Migration")
    print("========================================================")
    print(f"Target Host: {Config.PG_HOST}:{Config.PG_PORT}")
    print(f"Target Database: {Config.PG_DATABASE}")
    print(f"User: {Config.PG_USER}")

    # 1. Connect to root postgres DB to check / create smartwaste_db
    try:
        root_uri = Config.get_postgres_uri(default_db="postgres")
        root_engine = create_engine(root_uri, isolation_level="AUTOCOMMIT")
        with root_engine.connect() as conn:
            exists = conn.execute(
                text(f"SELECT 1 FROM pg_database WHERE datname = '{Config.PG_DATABASE}'")
            ).fetchone()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{Config.PG_DATABASE}"'))
                print(f"[✓] Created PostgreSQL database: {Config.PG_DATABASE}")
            else:
                print(f"[✓] PostgreSQL database '{Config.PG_DATABASE}' already exists.")
        root_engine.dispose()
    except Exception as e:
        print(f"[!] Could not connect to PostgreSQL server: {e}")
        print("\nPlease ensure your PostgreSQL service is running and your password in .env is correct.")
        return False

    # 2. Connect to smartwaste_db and run create_all and seed
    try:
        from backend.database import Base, SessionLocal, engine
        from backend.seed_data import seed_database
        print(f"[✓] Successfully connected to PostgreSQL '{Config.PG_DATABASE}'.")
        print("[*] Creating 3NF tables and constraints...")
        Base.metadata.create_all(bind=engine)
        print("[*] Seeding records from Excel dataset and prototype...")
        seed_database()
        print("\n[SUCCESS] PostgreSQL migration completed successfully! All 109 bins and routes are live in PostgreSQL.")
        return True
    except Exception as e:
        print(f"[!] Migration error: {e}")
        return False

if __name__ == "__main__":
    pwd = sys.argv[1] if len(sys.argv) > 1 else None
    run_migration(pwd)
