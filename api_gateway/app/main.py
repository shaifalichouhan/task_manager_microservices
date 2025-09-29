"""
API Gateway - Main application module.
Single entry point for all microservices.
"""
import logging
import time
from typing import Dict, Any, List
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from .core.config import get_settings
from .core.proxy import proxy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Create FastAPI application
app = FastAPI(
    title="API Gateway",
    description="Single entry point for Task Manager Microservices",
    version=settings.service_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add middleware
app.add_middleware(
    GZipMiddleware,
    minimum_size=1000
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=settings.allowed_methods,
    allow_headers=settings.allowed_headers,
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log all requests with timing"""
    start_time = time.time()
    
    # Skip logging for health checks to reduce noise
    if request.url.path not in ["/health", "/ping"]:
        logger.info(f"📨 {request.method} {request.url.path} - Client: {request.client.host}")
    
    response = await call_next(request)
    process_time = time.time() - start_time
    
    # Add timing header
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Gateway"] = "Task-Manager-Gateway"
    
    if request.url.path not in ["/health", "/ping"]:
        logger.info(f"📤 {request.method} {request.url.path} - {response.status_code} ({process_time:.3f}s)")
    
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "gateway_error",
                "status_code": exc.status_code,
                "message": exc.detail,
                "path": str(request.url.path),
                "timestamp": time.time(),
                "gateway": "task_manager_api_gateway"
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.exception(f"Unhandled exception in gateway: {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "type": "internal_gateway_error",
                "status_code": 500,
                "message": "Gateway internal error" if not settings.debug else str(exc),
                "path": str(request.url.path),
                "timestamp": time.time(),
                "gateway": "task_manager_api_gateway"
            }
        }
    )


# Root endpoint
@app.get("/", tags=["Gateway"])
async def root() -> Dict[str, Any]:
    """API Gateway root endpoint"""
    return {
        "service": "API Gateway",
        "version": settings.service_version,
        "status": "running",
        "message": "Task Manager API Gateway is operational",
        "services": list(settings.service_routes.keys()),
        "docs": "/docs",
        "timestamp": time.time()
    }


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """Comprehensive health check for gateway and downstream services"""
    start_time = time.time()
    
    health_status = {
        "gateway": {
            "service": "api_gateway",
            "version": settings.service_version,
            "status": "healthy",
            "timestamp": time.time()
        },
        "downstream_services": {},
        "overall_status": "healthy"
    }
    
    # Check each downstream service
    async with proxy:
        for service_name, config in settings.service_routes.items():
            service_health = await proxy.health_check_service(config["url"])
            health_status["downstream_services"][service_name] = service_health
            
            # Update overall status if any service is unhealthy
            if service_health["status"] != "healthy":
                health_status["overall_status"] = "degraded"
    
    health_status["response_time"] = time.time() - start_time
    
    # Return appropriate HTTP status
    status_code = 200
    if health_status["overall_status"] == "degraded":
        status_code = 200  # Still operational but with issues
    
    return JSONResponse(status_code=status_code, content=health_status)


# Service routes information
@app.get("/routes", tags=["Gateway"])
async def get_routes() -> Dict[str, Any]:
    """Get information about available routes"""
    return {
        "gateway_version": settings.service_version,
        "available_services": settings.service_routes,
        "routing_rules": {
            "auth_service": "Requests starting with /auth/* are routed to Auth Service",
            "task_service": "Requests starting with /api/v1/tasks/* are routed to Task Service",
            "notification_service": "Requests starting with /api/v1/notifications/* are routed to Notification Service"
        },
        "examples": {
            "register": "POST /auth/register",
            "login": "POST /auth/login", 
            "create_task": "POST /api/v1/tasks/",
            "get_tasks": "GET /api/v1/tasks/"
        }
    }


# Ping endpoint for simple connectivity check
@app.get("/ping", tags=["Health"])
async def ping():
    """Simple ping endpoint"""
    return {"status": "ok", "timestamp": time.time()}


# Catch-all route for proxying requests to microservices
@app.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
    tags=["Proxy"]
)
async def proxy_request(request: Request, path: str):
    """
    Proxy requests to appropriate microservices.
    This catch-all route handles all requests that don't match specific gateway endpoints.
    """
    # Skip proxying for gateway-specific endpoints
    gateway_endpoints = {"/", "/health", "/routes", "/ping", "/docs", "/redoc", "/openapi.json"}
    
    if f"/{path}" in gateway_endpoints or path in ["docs", "redoc", "openapi.json"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not found"
        )
    
    # Forward request to appropriate service
    async with proxy:
        return await proxy.forward_request(request)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )