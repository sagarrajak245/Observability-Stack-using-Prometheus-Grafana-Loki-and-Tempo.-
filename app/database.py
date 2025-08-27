from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool # Import StaticPool

SQLALCHEMY_DATABASE_URL = "sqlite:///./database/sql_app.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    # These arguments are recommended for SQLite with FastAPI
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
