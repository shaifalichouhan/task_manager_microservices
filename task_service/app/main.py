"""
Task Service - Main application module.
Professional microservice for task management with JWT authentication integration.
"""
import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from .core.config import get_settings
from .core.database import create_tables, check_database_connection, get_database_info
from .core.auth import auth_service
# Note: Import routers when we create them
# from .routers import tasks

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()


async def startup_tasks():
    """Execute startup tasks with proper error handling."""
    logger.info("🚀 Starting Task Service...")
    logger.info(f"Service: {settings.service_name} v{settings.service_version}")
    logger.info(f"Environment: {'Development' if settings.debug else 'Production'}")
    
    # Initialize database with retry logic
    max_retries = 10
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting database connection (attempt {attempt + 1}/{max_retries})")
            
            # Check database connection
            if check_database_connection():
                logger.info("✅ Database connection established")
                
                # Create tables
                create_tables()
                logger.info("✅ Database tables initialized")
                
                # Log database info
                db_info = get_database_info()
                logger.info(f"Database: {db_info.get('database_name')} ({db_info.get('mysql_version')})")
                
                break
            else:
                raise OperationalError("Database connection failed", None, None)
                
        except OperationalError as e:
            logger.warning(f"Database connection failed (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error("❌ Failed to connect to database after all retries")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Database connection failed"
                )
        except Exception as e:
            logger.error(f"Unexpected error during startup: {e}")
            raise
    
    # Check Auth Service connectivity
    try:
        auth_healthy = await auth_service.health_check()
        if auth_healthy:
            logger.info("✅ Auth Service connection verified")
        else:
            logger.warning("⚠️  Auth Service is not responding (service will continue)")
    except Exception as e:
        logger.warning(f"⚠️  Could not verify Auth Service: {e} (service will continue)")
    
    logger.info("✅ Task Service startup completed successfully")


async def shutdown_tasks():
    """Execute shutdown tasks."""
    logger.info("🛑 Shutting down Task Service...")
    # Add any cleanup tasks here
    logger.info("✅ Task Service shutdown completed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    await startup_tasks()
    yield
    # Shutdown
    await shutdown_tasks()


# Create FastAPI application with professional configuration
app = FastAPI(
    title=settings.service_name.title().replace('_', ' '),
    description="Professional microservice for task management with JWT authentication",
    version=settings.service_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan
)


# Add middleware stack
app.add_middleware(
    GZipMiddleware,
    minimum_size=1000
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log all incoming requests with timing."""
    start_time = time.time()
    
    # Log request
    logger.debug(f"📨 {request.method} {request.url.path} - Client: {request.client.host}")
    
    # Process request
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log response
        logger.debug(
            f"📤 {request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.3f}s"
        )
        
        # Add timing header
        response.headers["X-Process-Time"] = str(process_time)
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"❌ {request.method} {request.url.path} - "
            f"Error: {str(e)} - "
            f"Time: {process_time:.3f}s"
        )
        raise


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with consistent error format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "http_error",
                "status_code": exc.status_code,
                "message": exc.detail,
                "path": str(request.url.path),
                "timestamp": time.time()
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.exception(f"Unhandled exception in {request.method} {request.url.path}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "type": "internal_error",
                "status_code": 500,
                "message": "Internal server error" if not settings.debug else str(exc),
                "path": str(request.url.path),
                "timestamp": time.time()
            }
        }
    )


# Root endpoint
@app.get("/", tags=["Root"])
async def root() -> Dict[str, Any]:
    """Root endpoint with service information."""
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "status": "running",
        "message": "Task Service is operational",
        "docs_url": "/docs" if settings.debug else "Documentation disabled in production",
        "timestamp": time.time()
    }