"""
Tenant-aware helper functions for multi-tenant operations

Provides utilities for adding tenant_id to database operations
"""
from fastapi import Request
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def get_tenant_id(request: Request) -> int:
    """
    Extract tenant_id from request state (set by TenantMiddleware)
    
    Args:
        request: FastAPI Request object
        
    Returns:
        tenant_id: Integer tenant ID (0 for development)
    """
    tenant_id = getattr(request.state, 'tenant_id', 0)
    logger.info(f"[get_tenant_id] Extracted tenant_id={tenant_id} from request.state")
    logger.info(f"[get_tenant_id] request.state attributes: {dir(request.state)}")
    logger.info(f"[get_tenant_id] X-Tenant-ID header: {request.headers.get('X-Tenant-ID', 'NOT FOUND')}")
    return tenant_id


def get_user_id(request: Request) -> int:
    """
    Extract user_id from request state (set by TenantMiddleware)
    
    Args:
        request: FastAPI Request object
        
    Returns:
        user_id: Integer user ID (0 for development)
    """
    user_id = getattr(request.state, 'user_id', 0)
    return user_id
