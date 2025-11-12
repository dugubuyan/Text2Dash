"""
MySQL数据库适配器
"""
from typing import Dict, Any
from .base import DatabaseAdapter


class MySQLAdapter(DatabaseAdapter):
    """MySQL数据库适配器"""
    
    def get_connection_string(self, config: Dict[str, Any]) -> str:
        """构建MySQL连接字符串"""
        username = config.get('username', '')
        password = config.get('password', '')
        url = config.get('url', '')
        
        if username and password:
            return f"mysql+pymysql://{username}:{password}@{url}"
        else:
            return f"mysql+pymysql://{url}"
    
    def get_driver_name(self) -> str:
        """获取MySQL驱动名称"""
        return "mysql+pymysql"
    
    def get_connect_args(self) -> Dict[str, Any]:
        """获取MySQL连接参数"""
        return {}
    
    def format_identifier(self, name: str) -> str:
        """MySQL使用反引号格式化标识符"""
        return f"`{name}`"
    
    def get_db_type(self) -> str:
        """返回数据库类型"""
        return "mysql"
