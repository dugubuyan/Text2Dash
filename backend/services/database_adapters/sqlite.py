"""
SQLite数据库适配器
"""
from typing import Dict, Any
from .base import DatabaseAdapter


class SQLiteAdapter(DatabaseAdapter):
    """SQLite数据库适配器"""
    
    def get_connection_string(self, config: Dict[str, Any]) -> str:
        """构建SQLite连接字符串"""
        url = config.get('url', '')
        return url
    
    def get_driver_name(self) -> str:
        """获取SQLite驱动名称"""
        return "sqlite"
    
    def get_connect_args(self) -> Dict[str, Any]:
        """获取SQLite连接参数"""
        return {"check_same_thread": False}
    
    def format_identifier(self, name: str) -> str:
        """SQLite使用双引号或方括号格式化标识符"""
        return f'"{name}"'
    
    def get_db_type(self) -> str:
        """返回数据库类型"""
        return "sqlite"
