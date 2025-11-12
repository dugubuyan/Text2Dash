"""
数据库适配器基类
定义所有数据库适配器必须实现的接口
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class DatabaseAdapter(ABC):
    """数据库适配器基类"""
    
    @abstractmethod
    def get_connection_string(self, config: Dict[str, Any]) -> str:
        """
        构建数据库连接字符串
        
        Args:
            config: 数据库配置字典，包含 url, username, password 等
            
        Returns:
            数据库连接字符串
        """
        pass
    
    @abstractmethod
    def get_driver_name(self) -> str:
        """
        获取SQLAlchemy驱动名称
        
        Returns:
            驱动名称，如 'mysql+pymysql', 'postgresql+psycopg2'
        """
        pass
    
    @abstractmethod
    def get_connect_args(self) -> Dict[str, Any]:
        """
        获取数据库连接参数
        
        Returns:
            连接参数字典
        """
        pass
    
    @abstractmethod
    def format_identifier(self, name: str) -> str:
        """
        格式化标识符（表名、列名）
        
        Args:
            name: 标识符名称
            
        Returns:
            格式化后的标识符
        """
        pass
    
    def get_db_type(self) -> str:
        """
        获取数据库类型名称
        
        Returns:
            数据库类型，如 'mysql', 'postgresql', 'sqlite'
        """
        return self.__class__.__name__.replace('Adapter', '').lower()
