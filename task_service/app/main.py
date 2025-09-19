import logging
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Task Service",
    version="1.0.0",
    description="Task Management Microservice"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and initialize components with error handling
try:
    from .core.config import get_settings
    settings = get_settings()
    logger.info("Settings loaded successfully")
except Exception as e:
    logger.error(f"Failed to load settings: {e}")
    # Create minimal settings
    class MinimalSettings:
        API_PREFIX = "/api/v1"
    settings = MinimalSettings()

try:
    from .core.database import init_db, check_db_connection
    logger.info("Database module loaded successfully")
except Exception as e:
    logger.error(f"Failed to load database module: {e}")
    init_db = None
    check_db_connection = None

# Startup event
@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    logger.info("Starting Task Service...")
    
    # Initialize database if available
    if init_db:
        try:
            for attempt in range(3):
                try:
                    if init_db():
                        logger.info("Database initialized successfully")
                        break
                except Exception as e:
                    logger.warning(f"Database init attempt {attempt + 1} failed: {e}")
                    if attempt < 2:
                        time.sleep(5)
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
    
    logger.info("Task Service startup completed")

# Basic endpoints
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
        health_status = {
            "service": "task_service",
            "version": "1.0.0",
            "status": "healthy"
        }
        
        # Check database if available
        if check_db_connection:
            try:
                db_healthy = check_db_connection()
                health_status["database"] = "connected" if db_healthy else "disconnected"
            except Exception as e:
                health_status["database"] = f"error: {str(e)}"
        
        return health_status
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")

@app.get("/metrics")
async def metrics():
    """Metrics endpoint"""
    return {
        "service": "task_service",
        "version": "1.0.0",
        "status": "running"
    }

# Import and include task router
try:
    from .routers.tasks import router as task_router
    app.include_router(
        task_router, 
        prefix=f"{settings.API_PREFIX}/tasks", 
        tags=["tasks"]
    )
    logger.info("Task router included successfully")
except Exception as e:
    logger.error(f"Failed to include task router: {e}")
    # Add a debug endpoint to show the error
    @app.get("/router-debug")
    async def router_debug():
        return {"error": f"Task router failed to load: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)