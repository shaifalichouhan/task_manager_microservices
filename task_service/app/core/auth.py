"""
Authentication module for Task Service.
Handles JWT validation through Auth Service integration.
"""
import logging
from typing import Optional, Dict, Any
import httpx
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .config import get_settings

# Configure logging
logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer(
    scheme_name="Bearer Token",
    description="JWT Bearer token from Auth Service"
)

# Get settings
settings = get_settings()


class CurrentUser:
    """Represents the current authenticated user."""
    
    def __init__(self, user_id: int, email: str, username: str, **kwargs):
        self.user_id = user_id
        self.email = email
        self.username = username
        self.extra_data = kwargs
    
    def __str__(self):
        return f"User(id={self.user_id}, email={self.email})"
    
    def __repr__(self):
        return self.__str__()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CurrentUser":
        """Create CurrentUser from dictionary."""
        return cls(
            user_id=data.get("id"),
            email=data.get("email"),
            username=data.get("username"),
            **{k: v for k, v in data.items() if k not in ["id", "email", "username"]}
        )


class AuthService:
    """Service client for Auth Service integration."""
    
    def __init__(self):
        self.base_url = settings.auth_service_url
        self.timeout = settings.auth_service_timeout
        self.retries = settings.auth_service_retries
    
    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify JWT token with Auth Service.
        
        Args:
            token: JWT token to verify
            
        Returns:
            dict: User information if token is valid, None otherwise
        """
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        for attempt in range(self.retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    logger.debug(f"Verifying token with Auth Service (attempt {attempt + 1})")
                    
                    response = await client.get(
                        f"{self.base_url}/auth/verify",
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        logger.debug("Token verification successful")
                        return result
                    elif response.status_code == 401:
                        logger.warning("Token verification failed: invalid token")
                        return None
                    else:
                        logger.warning(f"Auth Service returned status {response.status_code}")
                        if attempt == self.retries - 1:
                            return None
                        continue
                        
            except httpx.TimeoutException:
                logger.warning(f"Auth Service timeout (attempt {attempt + 1})")
                if attempt == self.retries - 1:
                    logger.error("Auth Service timeout after all retries")
                    return None
            except httpx.ConnectError:
                logger.warning(f"Auth Service connection error (attempt {attempt + 1})")
                if attempt == self.retries - 1:
                    logger.error("Auth Service connection failed after all retries")
                    return None
            except Exception as e:
                logger.error(f"Unexpected error during token verification: {e}")
                if attempt == self.retries - 1:
                    return None
        
        return None
    
    async def get_user_info(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get current user information from Auth Service.
        
        Args:
            token: JWT token
            
        Returns:
            dict: User information if token is valid, None otherwise
        """
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/auth/me",
                    headers=headers
                )
                
                if response.status_code == 200:
                    user_info = response.json()
                    logger.debug(f"Retrieved user info for user_id: {user_info.get('id')}")
                    return user_info
                else:
                    logger.warning(f"Failed to get user info: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None
    
    async def health_check(self) -> bool:
        """
        Check if Auth Service is healthy.
        
        Returns:
            bool: True if Auth Service is healthy
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Auth Service health check failed: {e}")
            return False


# Global auth service instance
auth_service = AuthService()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> CurrentUser:
    """
    Dependency to get current authenticated user.
    
    Args:
        credentials: HTTP Bearer credentials from request
        
    Returns:
        CurrentUser: Current authenticated user
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    
    # First verify token
    verification_result = await auth_service.verify_token(token)
    if not verification_result or not verification_result.get("valid"):
        logger.warning("Token verification failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user information
    user_info = await auth_service.get_user_info(token)
    if not user_info:
        logger.warning("Failed to get user information")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create CurrentUser instance
    try:
        current_user = CurrentUser.from_dict(user_info)
        logger.debug(f"Authenticated user: {current_user}")
        return current_user
    except Exception as e:
        logger.error(f"Error creating CurrentUser: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal authentication error"
        )


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[CurrentUser]:
    """
    Optional dependency to get current user.
    Returns None if no valid token is provided.
    
    Args:
        credentials: Optional HTTP Bearer credentials
        
    Returns:
        CurrentUser or None: Current user if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None