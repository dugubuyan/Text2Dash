"""
数据库适配器模块
提供统一的数据库访问接口，支持多种数据库类型
"""
from .base import DatabaseAdapter
from .factory import DatabaseAdapterFactory
from .mysql import MySQLAdapter
from .postgresql import PostgreSQLAdapter
from .sqlite import SQLiteAdapter

__all__ = [
    'DatabaseAdapter',
    'DatabaseAdapterFactory',
    'MySQLAdapter',
    'PostgreSQLAdapter',
    'SQLiteAdapter',
]
