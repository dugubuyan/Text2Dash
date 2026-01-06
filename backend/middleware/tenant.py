"""
Tenant middleware for multi-tenant support.
Extracts tenant_id from request headers and stores in request.state.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract tenant information from request headers.
    Sets request.state.tenant_id, user_id, and username for use in routes.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Extract headers
        tenant_id_str = request.headers.get("X-Tenant-ID")
        user_id = request.headers.get("X-User-ID")
        username = request.headers.get("X-Username")
        
        # Parse tenant_id
        if tenant_id_str:
            try:
                request.state.tenant_id = int(tenant_id_str)
                logger.info(f"[TenantMiddleware] Extracted tenant_id={request.state.tenant_id} from header")
            except ValueError:
                logger.warning(f"[TenantMiddleware] Invalid tenant_id format: {tenant_id_str}, defaulting to 0")
                request.state.tenant_id = 0
        else:
            logger.info(f"[TenantMiddleware] No X-Tenant-ID header found, defaulting to 0")
            request.state.tenant_id = 0
        
        # Store user information
        request.state.user_id = user_id
        request.state.username = username
        
        logger.info(
            f"[TenantMiddleware] Request: {request.method} {request.url.path} | "
            f"Tenant: {request.state.tenant_id} | User: {request.state.user_id or 'anonymous'}"
        )
        
        response = await call_next(request)
        return response
