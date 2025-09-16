from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings
import os

# Debug: Print the database URL (remove in production)
print(f"🔍 Connecting to database: {settings.DATABASE_URL}")

# Ensure we have a valid database URL
if not settings.DATABASE_URL or settings.DATABASE_URL.strip() == "":
    # Fallback database URL
    database_url = "postgresql+psycopg2://postgres:postgres@postgres_db:5432/task_manager"
    print(f"⚠️  Using fallback DATABASE_URL: {database_url}")
else:
    database_url = settings.DATABASE_URL

try:
    engine = create_engine(database_url)
    print("✅ Database engine created successfully")
except Exception as e:
    print(f"❌ Error creating database engine: {e}")
    raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()