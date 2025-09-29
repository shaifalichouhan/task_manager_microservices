"""
HTTP Proxy client for forwarding requests to microservices.
"""
import logging
import time
from typing import Optional, Dict, Any
import httpx
from fastapi import HTTPException, status, Request, Response
from fastapi.responses import JSONResponse

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ServiceProxy:
    """HTTP proxy for forwarding requests to microservices"""
    
    def __init__(self):
        # Configure HTTP client with connection pooling
        limits = httpx.Limits(
            max_keepalive_connections=settings.connection_pool_limits,
            max_connections=settings.connection_pool_limits
        )
        
        self.client = httpx.AsyncClient(
            timeout=settings.request_timeout,
            limits=limits,
            follow_redirects=True
        )
        
        # Service routing configuration
        self.service_routes = settings.service_routes
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def get_service_url(self, path: str) -> Optional[tuple]:
        """
        Get service URL and cleaned path based on request path.
        
        Args:
            path: Request path (e.g., /auth/login, /api/v1/tasks/)
            
        Returns:
            tuple: (service_url, cleaned_path) or None if no match
        """
        for service_name, config in self.service_routes.items():
            prefix = config["prefix"]
            
            if path.startswith(prefix):
                # Remove the prefix from path for the downstream service
                cleaned_path = path[len(prefix):]
                if not cleaned_path.startswith('/'):
                    cleaned_path = '/' + cleaned_path
                
                return config["url"], cleaned_path
        
        return None, None
    
    def prepare_headers(self, request: Request) -> Dict[str, str]:
        """
        Prepare headers for forwarding to downstream service.
        
        Args:
            request: FastAPI request object
            
        Returns:
            dict: Headers to forward
        """
        # Start with original headers
        headers = dict(request.headers)
        
        # Remove hop-by-hop headers that shouldn't be forwarded
        hop_by_hop_headers = {
            'connection', 'keep-alive', 'proxy-authenticate',
            'proxy-authorization', 'te', 'trailers', 'transfer-encoding',
            'upgrade', 'host'
        }
        
        for header in hop_by_hop_headers:
            headers.pop(header, None)
        
        # Add proxy identification
        headers['X-Forwarded-By'] = 'API-Gateway'
        headers['X-Gateway-Version'] = settings.service_version
        
        # Handle client IP forwarding
        client_ip = request.client.host if request.client else 'unknown'
        headers['X-Forwarded-For'] = headers.get('X-Forwarded-For', client_ip)
        headers['X-Real-IP'] = client_ip
        
        return headers
    
    async def forward_request(
        self,
        request: Request,
        method: str = None,
        body: bytes = None
    ) -> Response:
        """
        Forward request to appropriate microservice.
        
        Args:
            request: FastAPI request object
            method: HTTP method override
            body: Request body override
            
        Returns:
            Response: Response from downstream service
        """
        start_time = time.time()
        
        # Determine target service
        service_url, cleaned_path = self.get_service_url(request.url.path)
        
        if not service_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No service found for path: {request.url.path}"
            )
        
        # Prepare request details
        method = method or request.method
        url = f"{service_url.rstrip('/')}{cleaned_path}"
        if request.url.query:
            url += f"?{request.url.query}"
        
        headers = self.prepare_headers(request)
        
        # Get request body if not provided
        if body is None:
            try:
                body = await request.body()
            except Exception as e:
                logger.error(f"Error reading request body: {e}")
                body = b''
        
        # Log request
        logger.info(f"Proxying {method} {request.url.path} -> {url}")
        
        # Forward request with retry logic
        for attempt in range(settings.max_retries):
            try:
                response = await self.client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    content=body
                )
                
                # Log successful response
                duration = time.time() - start_time
                logger.info(
                    f"Response: {method} {request.url.path} -> "
                    f"{response.status_code} ({duration:.3f}s)"
                )
                
                # Prepare response headers
                response_headers = dict(response.headers)
                
                # Remove hop-by-hop headers from response
                for header in ['connection', 'transfer-encoding', 'content-encoding']:
                    response_headers.pop(header, None)
                
                # Add gateway headers
                response_headers['X-Gateway-Service'] = service_url
                response_headers['X-Gateway-Duration'] = str(duration)
                
                # Return response with original status code and headers
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=response_headers,
                    media_type=response.headers.get('content-type')
                )
                
            except httpx.TimeoutException:
                logger.warning(f"Timeout forwarding to {service_url} (attempt {attempt + 1})")
                if attempt == settings.max_retries - 1:
                    raise HTTPException(
                        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                        detail=f"Service timeout: {service_url}"
                    )
            
            except httpx.ConnectError:
                logger.warning(f"Connection error to {service_url} (attempt {attempt + 1})")
                if attempt == settings.max_retries - 1:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=f"Service unavailable: {service_url}"
                    )
            
            except Exception as e:
                logger.error(f"Unexpected error forwarding request: {e}")
                if attempt == settings.max_retries - 1:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Gateway error occurred"
                    )
        
        # Should not reach here
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Request forwarding failed"
        )
    
    async def health_check_service(self, service_url: str) -> Dict[str, Any]:
        """
        Check health of a downstream service.
        
        Args:
            service_url: Service URL to check
            
        Returns:
            dict: Health status information
        """
        try:
            response = await self.client.get(
                f"{service_url}/health",
                timeout=10
            )
            
            return {
                "url": service_url,
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds()
            }
        except Exception as e:
            return {
                "url": service_url,
                "status": "unhealthy", 
                "error": str(e)
            }


# Global proxy instance
proxy = ServiceProxy()