"""
数据库连接池监控工具
"""
from typing import Dict, Any
from ..database import get_database


def get_pool_status() -> Dict[str, Any]:
    """
    获取数据库连接池状态
    
    Returns:
        包含连接池统计信息的字典
    """
    db = get_database()
    pool = db.engine.pool
    
    return {
        "pool_size": pool.size(),  # 连接池大小
        "checked_in": pool.checkedin(),  # 可用连接数
        "checked_out": pool.checkedout(),  # 正在使用的连接数
        "overflow": pool.overflow(),  # 溢出连接数
        "total_connections": pool.size() + pool.overflow(),  # 总连接数
        "status": "healthy" if pool.checkedin() > 0 else "busy"
    }


def print_pool_status():
    """打印连接池状态（用于调试）"""
    status = get_pool_status()
    print("\n=== 数据库连接池状态 ===")
    print(f"连接池大小: {status['pool_size']}")
    print(f"可用连接: {status['checked_in']}")
    print(f"使用中连接: {status['checked_out']}")
    print(f"溢出连接: {status['overflow']}")
    print(f"总连接数: {status['total_connections']}")
    print(f"状态: {status['status']}")
    print("========================\n")


if __name__ == "__main__":
    print_pool_status()
