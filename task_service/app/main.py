
import logging
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .core.rabbitmq import rabbitmq_publisher

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Task Service",
    description="Microservice for task management with JWT authentication",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    # Import settings
    from .core.config import get_settings
    settings = get_settings()
    logger.info("Settings loaded successfully")
    
    # Import database
    from .core.database import init_db, check_db_connection
    logger.info("Database module loaded successfully")
    
    # Import and include task router
    from .routers import tasks
    
    # Use api_prefix instead of API_PREFIX
    app.include_router(
        tasks.router, 
        prefix=settings.api_prefix + "/tasks",  # Use lowercase api_prefix
        tags=["tasks"]
    )
    logger.info("Task router included successfully")
    
except Exception as e:
    logger.error(f"Failed to include task router: {e}")


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Starting Task Service...")
    try:
        # Initialize database
        if init_db():
            logger.info("Database initialized successfully")
        else:
            logger.error("Database initialization failed")
    except Exception as e:
        logger.error(f"Startup error: {e}")
    
    logger.info("Task Service startup completed")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "task_service",
        "version": "1.0.0",
        "status": "running",
        "message": "Task Service is operational"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        db_healthy = check_db_connection()
        
        return {
            "service": "task_service",
            "version": "1.0.0",
            "status": "healthy" if db_healthy else "unhealthy",
            "database": "connected" if db_healthy else "disconnected",
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "service": "task_service",
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }


@app.get("/debug")
async def debug_info():
    """Debug information endpoint"""
    try:
        from .core.config import get_settings
        settings = get_settings()
        
        return {
            "settings": {
                "service_name": settings.service_name,
                "api_prefix": settings.api_prefix,  # Show the correct attribute name
                "database_url": "***HIDDEN***",
                "auth_service_url": settings.auth_service_url
            },
            "routes": [{"path": route.path, "methods": list(route.methods)} for route in app.routes]
        }
    except Exception as e:
        return {"error": str(e)}

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Starting Task Service...")
    try:
        # Initialize database
        if init_db():
            logger.info("Database initialized successfully")
        else:
            logger.error("Database initialization failed")
        
        # Initialize RabbitMQ connection
        if rabbitmq_publisher.connect():
            logger.info("RabbitMQ connection established")
        else:
            logger.warning("RabbitMQ connection failed - events will not be published")
            
    except Exception as e:
        logger.error(f"Startup error: {e}")
    
    logger.info("Task Service startup completed")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Task Service...")
    rabbitmq_publisher.close()
    logger.info("Task Service shutdown completed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)