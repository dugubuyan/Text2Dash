"""
Multi-tenant middleware for Text2Dash

Extracts tenant_id from X-Tenant-ID header (injected by API Gateway)
and stores it in request.state for use by routes.
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract tenant information from request headers.
    
    The API Gateway injects X-Tenant-ID and X-User-ID headers after
    authentication. This middleware extracts them and stores in request.state.
    
    For development mode (direct access without gateway), defaults to tenant_id=0.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Extract tenant and user information from headers
        tenant_id = request.headers.get('X-Tenant-ID', '0')
        user_id = request.headers.get('X-User-ID', '0')
        username = request.headers.get('X-Username', 'unknown')
        
        try:
            tenant_id = int(tenant_id)
            user_id = int(user_id)
        except ValueError:
            logger.warning(f"Invalid tenant/user ID in headers: tenant={tenant_id}, user={user_id}")
            tenant_id = 0
            user_id = 0
        
        # Store in request state
        request.state.tenant_id = tenant_id
        request.state.user_id = user_id
        request.state.username = username
        
        # Log for debugging (only in development)
        if tenant_id == 0:
            logger.debug(f"Request without gateway: {request.method} {request.url.path} (tenant_id=0)")
        else:
            logger.debug(f"Multi-tenant request: {request.method} {request.url.path} "
                        f"(tenant={tenant_id}, user={user_id})")
        
        response = await call_next(request)
        return response
