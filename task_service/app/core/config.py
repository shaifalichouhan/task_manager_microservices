"""
Configuration settings for Task Service.
Handles all environment variables and application settings.
"""
import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    url: str = Field(
        default="mysql+pymysql://taskuser:taskpassword@mysql_db:3306/task_manager",
        description="Complete database URL"
    )
    host: str = Field(default="mysql_db", description="Database host")
    port: int = Field(default=3306, description="Database port")
    name: str = Field(default="task_manager", description="Database name")
    user: str = Field(default="taskuser", description="Database username")
    password: str = Field(default="taskpassword", description="Database password")
    
    # Connection pool settings
    pool_size: int = Field(default=5, description="Connection pool size")
    max_overflow: int = Field(default=10, description="Max overflow connections")
    pool_timeout: int = Field(default=30, description="Pool timeout in seconds")
    pool_recycle: int = Field(default=3600, description="Pool recycle time in seconds")
    
    class Config:
        env_prefix = "DB_"


class AuthServiceSettings(BaseSettings):
    """Auth Service integration settings."""
    
    url: str = Field(
        default="http://auth_service:8000",
        description="Auth service base URL"
    )
    timeout: int = Field(default=30, description="Request timeout in seconds")
    retries: int = Field(default=3, description="Number of retries")
    
    class Config:
        env_prefix = "AUTH_SERVICE_"


class APISettings(BaseSettings):
    """API configuration settings."""
    
    prefix: str = Field(default="/api/v1", description="API prefix")
    max_page_size: int = Field(default=100, description="Maximum page size")
    default_page_size: int = Field(default=10, description="Default page size")
    
    class Config:
        env_prefix = "API_"


class SecuritySettings(BaseSettings):
    """Security configuration settings."""
    
    secret_key: str = Field(
        default="task-service-secret-key-change-in-production",
        description="Secret key for JWT validation"
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    
    class Config:
        env_prefix = ""


class Settings(BaseSettings):
    """Main application settings."""
    
    service_name: str = Field(default="task_service", description="Service name")
    service_version: str = Field(default="1.0.0", description="Service version")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    auth_service: AuthServiceSettings = Field(default_factory=AuthServiceSettings)
    api: APISettings = Field(default_factory=APISettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @property
    def database_url(self) -> str:
        """Get formatted database URL."""
        return (
            f"mysql+pymysql://{self.database.user}:"
            f"{self.database.password}@{self.database.host}:"
            f"{self.database.port}/{self.database.name}"
        )
    
    def model_dump_json(self, **kwargs) -> str:
        """Override to hide sensitive information."""
        data = self.model_dump(**kwargs)
        # Hide sensitive fields
        if "database" in data:
            data["database"]["password"] = "***HIDDEN***"
        if "security" in data:
            data["security"]["secret_key"] = "***HIDDEN***"
        return super().model_dump_json(**kwargs)


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Dependency to get settings instance."""
    return settings