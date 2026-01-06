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
        
        # 如果URL已经是完整的sqlite://格式，直接返回
        if url.startswith('sqlite://'):
            return url
        
        # 否则，将文件路径转换为sqlite://格式
        # SQLite URL格式: sqlite:///path/to/file.db (三个斜杠表示相对路径或绝对路径)
        return f'sqlite:///{url}'
    
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
