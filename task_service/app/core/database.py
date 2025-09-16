"""
Database configuration and session management for Task Service.
Provides SQLAlchemy engine, session factory, and database utilities.
"""
import logging
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from .config import get_settings

# Configure logging
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Create SQLAlchemy engine with connection pooling
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=settings.database.pool_size,
    max_overflow=settings.database.max_overflow,
    pool_timeout=settings.database.pool_timeout,
    pool_recycle=settings.database.pool_recycle,
    pool_pre_ping=True,  # Enable connection health checks
    echo=settings.debug,  # Log SQL queries in debug mode
    future=True  # Use SQLAlchemy 2.0 style
)

# Create session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

# Create declarative base for models
Base = declarative_base()


# Database event listeners for monitoring
@event.listens_for(engine, "connect")
def on_connect(dbapi_connection, connection_record):
    """Handle new database connections."""
    logger.info("New database connection established")
    
    # Set MySQL session variables for better performance
    with dbapi_connection.cursor() as cursor:
        cursor.execute("SET SESSION sql_mode='STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION'")
        cursor.execute("SET SESSION innodb_lock_wait_timeout=50")


@event.listens_for(engine, "checkout")
def on_checkout(dbapi_connection, connection_record, connection_proxy):
    """Handle connection checkout from pool."""
    logger.debug("Connection checked out from pool")


@event.listens_for(engine, "checkin")
def on_checkin(dbapi_connection, connection_record):
    """Handle connection checkin to pool."""
    logger.debug("Connection checked in to pool")


def get_db() -> Generator[Session, None, None]:
    """
    Database dependency for FastAPI.
    Provides a database session and handles cleanup.
    
    Yields:
        Session: SQLAlchemy database session
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


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    Use this for operations outside of FastAPI endpoints.
    
    Yields:
        Session: SQLAlchemy database session
    
    Example:
        with get_db_context() as db:
            user = db.query(User).first()
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database context error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def create_tables():
    """Create all database tables."""
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


def drop_tables():
    """Drop all database tables. Use with caution!"""
    try:
        logger.warning("Dropping all database tables...")
        Base.metadata.drop_all(bind=engine)
        logger.warning("All database tables dropped")
    except Exception as e:
        logger.error(f"Failed to drop database tables: {e}")
        raise


def check_database_connection() -> bool:
    """
    Check if database connection is working.
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        with engine.connect() as connection:
            result = connection.execute("SELECT 1 as health_check")
            row = result.fetchone()
            if row and row[0] == 1:
                logger.info("Database connection is healthy")
                return True
            else:
                logger.error("Database health check failed: unexpected result")
                return False
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


def get_database_info() -> dict:
    """
    Get database connection information.
    
    Returns:
        dict: Database information
    """
    try:
        with engine.connect() as connection:
            # Get MySQL version
            version_result = connection.execute("SELECT VERSION() as version")
            version = version_result.fetchone()[0] if version_result else "Unknown"
            
            # Get current database
            db_result = connection.execute("SELECT DATABASE() as db_name")
            db_name = db_result.fetchone()[0] if db_result else "Unknown"
            
            # Get connection info
            pool = engine.pool
            
            return {
                "database_name": db_name,
                "mysql_version": version,
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "status": "connected"
            }
    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        return {
            "status": "disconnected",
            "error": str(e)
        }