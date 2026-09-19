# app/db/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# For SQLite, we must set check_same_thread to False to prevent FastAPI from crashing
# when multiple asynchronous requests try to access the database.
connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

engine = create_engine(
    settings.DATABASE_URL, 
    connect_args=connect_args
)

# SessionLocal creates a temporary database connection for each request
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to inject the database session into our API routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()