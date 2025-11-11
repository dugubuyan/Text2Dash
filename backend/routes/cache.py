"""
缓存管理API路由
"""
from fastapi import APIRouter, status
from pydantic import BaseModel

from ..services.cache_service import get_cache_service
from ..utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/cache", tags=["cache"])


class CacheStatsResponse(BaseModel):
    """缓存统计响应"""
    size: int
    max_size: int
    hits: int
    misses: int
    hit_rate: str
    total_requests: int


@router.get("/stats", response_model=CacheStatsResponse, status_code=status.HTTP_200_OK)
async def get_cache_stats():
    """
    获取缓存统计信息
    """
    try:
        cache = get_cache_service()
        stats = cache.get_stats()
        
        return CacheStatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"获取缓存统计失败: {str(e)}", exc_info=True)
        raise


@router.post("/clear", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cache():
    """
    清空所有缓存
    """
    try:
        cache = get_cache_service()
        cache.clear()
        
        logger.info("缓存已清空")
        return None
        
    except Exception as e:
        logger.error(f"清空缓存失败: {str(e)}", exc_info=True)
        raise


@router.post("/cleanup", status_code=status.HTTP_200_OK)
async def cleanup_expired_cache():
    """
    清理过期的缓存条目
    """
    try:
        cache = get_cache_service()
        count = cache.cleanup_expired()
        
        logger.info(f"清理过期缓存: {count} 条")
        return {"cleaned": count}
        
    except Exception as e:
        logger.error(f"清理过期缓存失败: {str(e)}", exc_info=True)
        raise
