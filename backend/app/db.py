from sqlalchemy import create_engine
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://geo:geo@db:5432/geodb")

def get_engine():
    return create_engine(DATABASE_URL, future=True)
