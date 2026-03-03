from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Default to SQLite for easy testing, but configurable to Postgres via .env
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./acertemos.db")

# Fallback to sqlite for local testing if needed, though user asked for Postgres
if not DATABASE_URL.startswith("postgresql"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
