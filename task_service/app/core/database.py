import os
import logging
from typing import Generator
from sqlalchemy import create_engine, event, Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)

# Database URL from environment variable
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "mysql+pymysql://taskuser:taskpassword@mysql_db:3306/task_manager"
)

# Create SQLAlchemy engine with proper configuration
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=os.getenv("DEBUG", "false").lower() == "true"
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine
)

# Base class for models
Base = declarative_base()

# Database event listeners for monitoring
@event.listens_for(engine, "connect")
def receive_connect(dbapi_connection, connection_record):
    """Event listener for database connections"""
    logger.info("Database connection established")

@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Event listener for connection checkout"""
    logger.debug("Database connection checked out from pool")

def get_db() -> Generator[Session, None, None]:
    """
    Database dependency for FastAPI
    
    Yields:
        Session: Database session
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def init_db() -> bool:
    """
    Initialize database tables
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Import all models here to ensure they are registered
        from ..models import task  # Import task model
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

def check_db_connection() -> bool:
    """
    Check database connectivity
    
    Returns:
        bool: True if connected, False otherwise
    """
    try:
        with engine.connect() as connection:
            connection.execute("SELECT 1")
        logger.info("Database connection check successful")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False