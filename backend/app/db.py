from sqlalchemy import create_engine
import os

DB_USER = os.getenv("POSTGRES_USER", "geo")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "geo")
DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = os.getenv("DB_PORT", "5432")

def get_engine(city: str = "delhi"):
    db_name = f"geodb_{city}"
    url = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{db_name}"
    return create_engine(url, future=True)


def get_postgres_engine():
    url = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/postgres"
    return create_engine(url, future=True)
