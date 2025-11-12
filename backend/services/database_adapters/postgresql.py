"""
PostgreSQL数据库适配器
"""
from typing import Dict, Any
from .base import DatabaseAdapter


class PostgreSQLAdapter(DatabaseAdapter):
    """PostgreSQL数据库适配器"""
    
    def get_connection_string(self, config: Dict[str, Any]) -> str:
        """构建PostgreSQL连接字符串"""
        username = config.get('username', '')
        password = config.get('password', '')
        url = config.get('url', '')
        
        if username and password:
            return f"postgresql+psycopg2://{username}:{password}@{url}"
        else:
            return f"postgresql+psycopg2://{url}"
    
    def get_driver_name(self) -> str:
        """获取PostgreSQL驱动名称"""
        return "postgresql+psycopg2"
    
    def get_connect_args(self) -> Dict[str, Any]:
        """获取PostgreSQL连接参数"""
        return {}
    
    def format_identifier(self, name: str) -> str:
        """PostgreSQL使用双引号格式化标识符（仅在需要时）"""
        return f'"{name}"'
    
    def get_db_type(self) -> str:
        """返回数据库类型"""
        return "postgresql"
