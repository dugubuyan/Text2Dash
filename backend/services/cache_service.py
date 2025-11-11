"""
缓存服务
使用内存缓存来存储LLM结果，提高重复查询的性能
"""
import hashlib
import json
import time
from typing import Any, Optional, Dict
from collections import OrderedDict
from ..utils.logger import get_logger

logger = get_logger(__name__)


class CacheService:
    """简单的内存缓存服务（LRU策略）"""
    
    def __init__(self, max_size: int = 100, default_ttl: int = 3600):
        """
        初始化缓存服务
        
        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认过期时间（秒）
        """
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.hits = 0
        self.misses = 0
        
        logger.info(f"缓存服务初始化: max_size={max_size}, default_ttl={default_ttl}s")
    
    def _generate_key(self, prefix: str, data: Any) -> str:
        """
        生成缓存键
        
        Args:
            prefix: 键前缀
            data: 要缓存的数据（会被序列化）
        
        Returns:
            缓存键
        """
        # 将数据序列化为JSON字符串
        data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        
        # 生成哈希
        hash_obj = hashlib.md5(data_str.encode('utf-8'))
        hash_str = hash_obj.hexdigest()
        
        return f"{prefix}:{hash_str}"
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
        
        Returns:
            缓存的值，如果不存在或已过期则返回None
        """
        if key not in self.cache:
            self.misses += 1
            logger.debug(f"缓存未命中: {key}")
            return None
        
        entry = self.cache[key]
        
        # 检查是否过期
        if time.time() > entry['expires_at']:
            del self.cache[key]
            self.misses += 1
            logger.debug(f"缓存已过期: {key}")
            return None
        
        # 移动到末尾（LRU）
        self.cache.move_to_end(key)
        
        self.hits += 1
        logger.debug(f"缓存命中: {key}")
        
        return entry['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 要缓存的值
            ttl: 过期时间（秒），如果为None则使用默认值
        """
        if ttl is None:
            ttl = self.default_ttl
        
        # 如果缓存已满，删除最旧的条目
        if len(self.cache) >= self.max_size and key not in self.cache:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            logger.debug(f"缓存已满，删除最旧条目: {oldest_key}")
        
        # 添加或更新缓存
        self.cache[key] = {
            'value': value,
            'expires_at': time.time() + ttl,
            'created_at': time.time()
        }
        
        # 移动到末尾
        self.cache.move_to_end(key)
        
        logger.debug(f"缓存已设置: {key}, ttl={ttl}s")
    
    def delete(self, key: str) -> bool:
        """
        删除缓存值
        
        Args:
            key: 缓存键
        
        Returns:
            是否成功删除
        """
        if key in self.cache:
            del self.cache[key]
            logger.debug(f"缓存已删除: {key}")
            return True
        return False
    
    def clear(self) -> None:
        """清空所有缓存"""
        count = len(self.cache)
        self.cache.clear()
        logger.info(f"缓存已清空: {count} 条")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            统计信息字典
        """
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': f"{hit_rate:.2f}%",
            'total_requests': total_requests
        }
    
    def cleanup_expired(self) -> int:
        """
        清理过期的缓存条目
        
        Returns:
            清理的条目数
        """
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items()
            if current_time > entry['expires_at']
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.info(f"清理过期缓存: {len(expired_keys)} 条")
        
        return len(expired_keys)


# 全局缓存服务实例
_cache_service = None


def get_cache_service() -> CacheService:
    """
    获取全局缓存服务实例
    
    Returns:
        CacheService实例
    """
    global _cache_service
    
    if _cache_service is None:
        _cache_service = CacheService(
            max_size=100,  # 最多缓存100个查询结果
            default_ttl=3600  # 默认缓存1小时
        )
    
    return _cache_service
