"""
数据库适配器工厂
负责创建和管理数据库适配器实例
"""
from typing import Dict, Type
from .base import DatabaseAdapter
from .mysql import MySQLAdapter
from .postgresql import PostgreSQLAdapter
from .sqlite import SQLiteAdapter


class DatabaseAdapterFactory:
    """数据库适配器工厂类"""
    
    # 注册的适配器映射
    _adapters: Dict[str, Type[DatabaseAdapter]] = {
        "mysql": MySQLAdapter,
        "postgresql": PostgreSQLAdapter,
        "sqlite": SQLiteAdapter,
    }
    
    @classmethod
    def get_adapter(cls, db_type: str) -> DatabaseAdapter:
        """
        根据数据库类型获取对应的适配器实例
        
        Args:
            db_type: 数据库类型，如 'mysql', 'postgresql', 'sqlite'
            
        Returns:
            数据库适配器实例
            
        Raises:
            ValueError: 如果数据库类型不支持
        """
        db_type_lower = db_type.lower()
        adapter_class = cls._adapters.get(db_type_lower)
        
        if not adapter_class:
            raise ValueError(
                f"不支持的数据库类型: {db_type}。"
                f"支持的类型: {', '.join(cls._adapters.keys())}"
            )
        
        return adapter_class()
    
    @classmethod
    def register_adapter(cls, db_type: str, adapter_class: Type[DatabaseAdapter]):
        """
        注册新的数据库适配器
        
        Args:
            db_type: 数据库类型名称
            adapter_class: 适配器类
        """
        cls._adapters[db_type.lower()] = adapter_class
    
    @classmethod
    def get_supported_types(cls) -> list:
        """
        获取所有支持的数据库类型
        
        Returns:
            支持的数据库类型列表
        """
        return list(cls._adapters.keys())
    
    @classmethod
    def is_supported(cls, db_type: str) -> bool:
        """
        检查是否支持指定的数据库类型
        
        Args:
            db_type: 数据库类型
            
        Returns:
            是否支持
        """
        return db_type.lower() in cls._adapters
