import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DB_TYPE = os.getenv("DB_TYPE", "postgres")  # 'postgres' or 'sqlite'
    PG_HOST = os.getenv("PG_HOST", "localhost")
    PG_PORT = os.getenv("PG_PORT", "5432")
    PG_USER = os.getenv("PG_USER", "postgres")
    PG_PASSWORD = os.getenv("PG_PASSWORD", "")
    PG_DATABASE = os.getenv("PG_DATABASE", "smartwaste_db")
    
    # SQLite fallback path inside backend/data (ignored by live-server)
    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, "backend", "data")
    os.makedirs(DATA_DIR, exist_ok=True)
    SQLITE_PATH = os.path.join(DATA_DIR, "smartwaste.db")
    
    PORT = int(os.getenv("PORT", 5000))
    DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

    @classmethod
    def get_postgres_uri(cls, default_db=None):
        db_name = default_db if default_db else cls.PG_DATABASE
        pwd = f":{cls.PG_PASSWORD}" if cls.PG_PASSWORD else ""
        return f"postgresql+psycopg2://{cls.PG_USER}{pwd}@{cls.PG_HOST}:{cls.PG_PORT}/{db_name}"

    @classmethod
    def get_sqlite_uri(cls):
        return f"sqlite:///{cls.SQLITE_PATH}"
