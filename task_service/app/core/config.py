import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    """Application settings"""
    
    # App configuration
    APP_NAME: str = "Task Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Database configuration
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "mysql+pymysql://taskuser:taskpassword@mysql_db:3306/task_manager"
    )
    
    # Auth Service configuration
    AUTH_SERVICE_URL: str = os.getenv(
        "AUTH_SERVICE_URL",
        "http://auth_service:8000"
    )
    AUTH_SERVICE_TIMEOUT: int = int(os.getenv("AUTH_SERVICE_TIMEOUT", "30"))
    
    # API configuration
    API_PREFIX: str = "/api/v1"
    
    # Database pool settings
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    
    def __init__(self):
        """Initialize settings with debug output"""
        if self.DEBUG:
            print(f"Database URL: {self.DATABASE_URL}")
            print(f"Auth Service URL: {self.AUTH_SERVICE_URL}")
            print(f"Debug mode: {self.DEBUG}")

# Create settings instance
settings = Settings()

def get_settings() -> Settings:
    """Get application settings"""
    return settings