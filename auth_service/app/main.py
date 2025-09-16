from fastapi import FastAPI
import time
import logging
from sqlalchemy.exc import OperationalError
from sqlalchemy import text

from .core.database import engine, get_db
from .models import user
from .routers import auth

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app first
app = FastAPI(title="Auth Service", version="1.0.0")

def create_tables_with_retry(max_retries=10, delay=5):
    """Create database tables with retry logic"""
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting to connect to database (attempt {attempt + 1}/{max_retries})")
            user.Base.metadata.create_all(bind=engine)
            logger.info("✅ Database tables created successfully!")
            return True
        except OperationalError as e:
            logger.warning(f"Database connection failed (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                logger.error("❌ Failed to connect to database after all retries")
                raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise
    return False

# Event handlers
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    logger.info("🚀 Starting Auth Service...")
    create_tables_with_retry()
    logger.info("✅ Auth Service startup completed!")

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["authentication"])

@app.get("/")
def read_root():
    return {"message": "Auth Service is running!", "service": "auth_service"}

