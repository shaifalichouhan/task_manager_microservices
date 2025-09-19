import logging
from typing import Optional
import httpx
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Security scheme
security = HTTPBearer()

class AuthService:
    """Service for handling authentication with auth microservice"""
    
    def __init__(self):
        self.auth_service_url = settings.AUTH_SERVICE_URL
        self.timeout = settings.AUTH_SERVICE_TIMEOUT
    
    async def verify_token(self, token: str) -> Optional[dict]:
        """
        Verify JWT token with auth service
        
        Args:
            token: JWT token to verify
            
        Returns:
            dict: User information if valid, None if invalid
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.auth_service_url}/auth/verify",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    logger.warning("Invalid token provided")
                    return None
                else:
                    logger.error(f"Auth service error: {response.status_code}")
                    return None
                    
        except httpx.TimeoutException:
            logger.error("Auth service timeout")
            return None
        except httpx.RequestError as e:
            logger.error(f"Auth service request error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in token verification: {e}")
            return None
    
    async def get_user_info(self, token: str) -> Optional[dict]:
        """
        Get user information from auth service
        
        Args:
            token: JWT token
            
        Returns:
            dict: User information if successful
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.auth_service_url}/auth/me",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Failed to get user info: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None

# Create auth service instance
auth_service = AuthService()

async def verify_auth_service_connection() -> bool:
    """
    Verify connection to auth service
    
    Returns:
        bool: True if connection successful
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{settings.AUTH_SERVICE_URL}/health")
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Auth service connection check failed: {e}")
        return False

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    FastAPI dependency to get current authenticated user
    
    Args:
        credentials: Authorization credentials from request
        
    Returns:
        dict: User information
        
    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    
    # Verify token with auth service
    verification_result = await auth_service.verify_token(token)
    
    if not verification_result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get full user information
    user_info = await auth_service.get_user_info(token)
    
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_info

async def get_current_active_user(current_user: dict = Depends(get_current_user)) -> dict:
    """
    FastAPI dependency to get current active user
    
    Args:
        current_user: Current user from get_current_user dependency
        
    Returns:
        dict: Active user information
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user"
        )
    return current_user