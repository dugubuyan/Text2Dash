"""
日期时间辅助工具
用于统一处理时间序列化，确保前端能正确识别时区
"""
from datetime import datetime, timezone
from typing import Optional


def to_iso_string(dt: Optional[datetime]) -> Optional[str]:
    """
    将 datetime 对象转换为 ISO 8601 格式字符串（带 UTC 时区标识）
    
    Args:
        dt: datetime 对象（可以为 None）
        
    Returns:
        ISO 8601 格式字符串，带 'Z' 后缀表示 UTC 时区
        如果输入为 None，返回 None
        
    Examples:
        >>> dt = datetime(2024, 11, 3, 6, 30, 0)
        >>> to_iso_string(dt)
        '2024-11-03T06:30:00Z'
    """
    if dt is None:
        return None
    
    # 如果 datetime 对象没有时区信息，假设为 UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    # 转换为 UTC 时区
    dt_utc = dt.astimezone(timezone.utc)
    
    # 返回 ISO 8601 格式，使用 'Z' 后缀表示 UTC
    # 移除微秒部分以保持简洁
    return dt_utc.replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def utc_now() -> datetime:
    """
    获取当前 UTC 时间（带时区信息）
    
    Returns:
        带 UTC 时区信息的 datetime 对象
    """
    return datetime.now(timezone.utc)
