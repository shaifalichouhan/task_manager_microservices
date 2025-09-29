"""
Configuration settings for Task Service.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    """Application settings"""
    
    # Service information
    service_name: str = "task_service"
    service_version: str = "1.0.0"
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Database configuration
    database_url: str = os.getenv(
        "DATABASE_URL", 
        "mysql+pymysql://taskuser:taskpassword@mysql_db:3306/task_manager"
    )
    
    # Auth Service configuration  
    auth_service_url: str = os.getenv("AUTH_SERVICE_URL", "http://auth_service:8000")
    auth_service_timeout: int = int(os.getenv("AUTH_SERVICE_TIMEOUT", "30"))
    auth_service_retries: int = int(os.getenv("AUTH_SERVICE_RETRIES", "3"))
    
    # API configuration
    api_prefix: str = os.getenv("API_PREFIX", "/api/v1")
    max_page_size: int = int(os.getenv("MAX_PAGE_SIZE", "100"))
    default_page_size: int = int(os.getenv("DEFAULT_PAGE_SIZE", "10"))
    
    # Security
    secret_key: str = os.getenv(
        "SECRET_KEY", 
        "task-service-secret-key-change-in-production"
    )
    algorithm: str = os.getenv("ALGORITHM", "HS256")


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get settings instance."""
    return settings