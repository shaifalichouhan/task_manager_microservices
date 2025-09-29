"""
Configuration settings for API Gateway.
"""
import os
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    """API Gateway configuration settings"""
    
    # Service information
    service_name: str = os.getenv("SERVICE_NAME", "api_gateway")
    service_version: str = os.getenv("SERVICE_VERSION", "1.0.0")
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Microservice URLs
    auth_service_url: str = os.getenv("AUTH_SERVICE_URL", "http://auth_service:8000")
    task_service_url: str = os.getenv("TASK_SERVICE_URL", "http://task_service:8000") 
    notification_service_url: str = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification_service:8000")
    
    # Request configuration
    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))
    connection_pool_limits: int = int(os.getenv("CONNECTION_POOL_LIMITS", "100"))
    
    # CORS configuration
    allowed_origins: List[str] = os.getenv("ALLOWED_ORIGINS", "*").split(",")
    allowed_methods: List[str] = os.getenv("ALLOWED_METHODS", "*").split(",")
    allowed_headers: List[str] = os.getenv("ALLOWED_HEADERS", "*").split(",")
    
    # Rate limiting
    rate_limit_requests: int = int(os.getenv("RATE_LIMIT_REQUESTS", "1000"))
    rate_limit_window: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
    
    @property
    def service_routes(self) -> dict:
        """Get service routing configuration"""
        return {
            "auth": {
                "url": self.auth_service_url,
                "prefix": "/auth",
                "description": "Authentication Service"
            },
            "tasks": {
                "url": self.task_service_url, 
                "prefix": "/api/v1/tasks",
                "description": "Task Management Service"
            },
            "notifications": {
                "url": self.notification_service_url,
                "prefix": "/api/v1/notifications", 
                "description": "Notification Service"
            }
        }


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get settings instance"""
    return settings