"""
Notification Service - With Authentication Support
"""
import logging
import time
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Depends, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()

# Create FastAPI application
app = FastAPI(
    title="Notification Service",
    description="Task Manager Notification Service with Authentication",
    version="1.0.0"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for notifications
processed_notifications = []

# Pydantic models
class TaskEventData(BaseModel):
    title: str
    description: Optional[str] = None
    user_email: Optional[str] = None
    priority: Optional[str] = "medium"
    task_id: Optional[int] = None

class NotificationResponse(BaseModel):
    id: int
    timestamp: float
    event_type: str
    data: dict
    status: str

class NotificationStats(BaseModel):
    total_processed: int
    recent_notifications: int
    event_types: Dict[str, int]

# Authentication helper
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Verify JWT token with Auth Service"""
    token = credentials.credentials
    
    try:
        # Verify token with auth service
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                "http://auth_service:8000/auth/verify",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("valid"):
                    return result.get("email", "unknown")
            
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth service unavailable"
        )

@app.on_event("startup")
async def startup_event():
    """Startup event"""
    logger.info("Notification Service starting...")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "notification_service",
        "version": "1.0.0", 
        "status": "running",
        "message": "Notification Service is operational",
        "endpoints": {
            "health": "/health",
            "logs": "/logs (requires auth)",
            "webhook": "/webhook/task_created",
            "stats": "/stats (requires auth)"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "service": "notification_service",
        "version": "1.0.0",
        "status": "healthy",
        "notifications_processed": len(processed_notifications),
        "timestamp": time.time()
    }

@app.get("/logs", response_model=Dict[str, Any], dependencies=[Depends(verify_token)])
async def get_logs(
    limit: int = Query(50, ge=1, le=100, description="Number of logs to return")
):
    """
    Get processed notifications (requires authentication)
    This endpoint requires a valid JWT token from the Auth Service
    """
    try:
        recent_notifications = processed_notifications[-limit:] if limit else processed_notifications
        
        return {
            "total_processed": len(processed_notifications),
            "returned_count": len(recent_notifications),
            "notifications": recent_notifications,
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving logs: {str(e)}"
        )

@app.get("/stats", response_model=NotificationStats, dependencies=[Depends(verify_token)])
async def get_notification_stats():
    """Get notification statistics (requires authentication)"""
    try:
        # Calculate event type counts
        event_types = {}
        recent_count = 0
        current_time = time.time()
        
        for notification in processed_notifications:
            # Count by event type
            event_type = notification.get("event_type", "unknown")
            event_types[event_type] = event_types.get(event_type, 0) + 1
            
            # Count recent (last hour)
            if current_time - notification.get("timestamp", 0) < 3600:
                recent_count += 1
        
        return NotificationStats(
            total_processed=len(processed_notifications),
            recent_notifications=recent_count,
            event_types=event_types
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting stats: {str(e)}"
        )

@app.post("/webhook/task_created", response_model=Dict[str, Any])
async def handle_task_created(task_data: TaskEventData):
    """
    Handle task created events via webhook
    This endpoint can be called by other services to trigger notifications
    """
    try:
        # Log the notification
        logger.info(f"Task created notification: {task_data.title}")
        
        # Create notification record
        notification = {
            "id": len(processed_notifications) + 1,
            "timestamp": time.time(),
            "event_type": "task_created",
            "data": task_data.dict(),
            "status": "processed",
            "notification_methods": ["log", "webhook"],
            "processed_at": time.time()
        }
        
        # Store notification
        processed_notifications.append(notification)
        
        # Keep only last 1000 notifications
        if len(processed_notifications) > 1000:
            processed_notifications.pop(0)
        
        return {
            "status": "success",
            "message": "Task creation notification processed successfully",
            "notification_id": notification["id"],
            "timestamp": notification["timestamp"]
        }
        
    except Exception as e:
        logger.error(f"Error processing task created notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing notification: {str(e)}"
        )

@app.post("/webhook/task_updated", response_model=Dict[str, Any])
async def handle_task_updated(task_data: TaskEventData):
    """Handle task updated events via webhook"""
    try:
        logger.info(f"Task updated notification: {task_data.title}")
        
        notification = {
            "id": len(processed_notifications) + 1,
            "timestamp": time.time(),
            "event_type": "task_updated", 
            "data": task_data.dict(),
            "status": "processed"
        }
        
        processed_notifications.append(notification)
        
        return {
            "status": "success",
            "message": "Task update notification processed",
            "notification_id": notification["id"]
        }
    except Exception as e:
        logger.error(f"Error processing task updated notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.delete("/logs", dependencies=[Depends(verify_token)])
async def clear_logs():
    """Clear all notification logs (requires authentication)"""
    global processed_notifications
    count = len(processed_notifications)
    processed_notifications.clear()
    
    return {
        "status": "success",
        "message": f"Cleared {count} notification logs",
        "timestamp": time.time()
    }

@app.get("/test-auth")
async def test_auth(user_email: str = Depends(verify_token)):
    """Test authentication endpoint"""
    return {
        "message": "Authentication successful",
        "authenticated_user": user_email,
        "timestamp": time.time()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)