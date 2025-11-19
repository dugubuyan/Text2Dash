"""
数据库适配器测试
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from backend.services.database_adapters import (
    DatabaseAdapterFactory,
    MySQLAdapter,
    PostgreSQLAdapter,
    SQLiteAdapter,
)


class TestDatabaseAdapterFactory:
    """测试数据库适配器工厂"""
    
    def test_get_mysql_adapter(self):
        """测试获取MySQL适配器"""
        adapter = DatabaseAdapterFactory.get_adapter("mysql")
        assert isinstance(adapter, MySQLAdapter)
        assert adapter.get_db_type() == "mysql"
        assert adapter.get_driver_name() == "mysql+pymysql"
    
    def test_get_postgresql_adapter(self):
        """测试获取PostgreSQL适配器"""
        adapter = DatabaseAdapterFactory.get_adapter("postgresql")
        assert isinstance(adapter, PostgreSQLAdapter)
        assert adapter.get_db_type() == "postgresql"
        assert adapter.get_driver_name() == "postgresql+psycopg2"
    
    def test_get_sqlite_adapter(self):
        """测试获取SQLite适配器"""
        adapter = DatabaseAdapterFactory.get_adapter("sqlite")
        assert isinstance(adapter, SQLiteAdapter)
        assert adapter.get_db_type() == "sqlite"
        assert adapter.get_driver_name() == "sqlite"
    
    def test_case_insensitive(self):
        """测试数据库类型不区分大小写"""
        adapter1 = DatabaseAdapterFactory.get_adapter("MySQL")
        adapter2 = DatabaseAdapterFactory.get_adapter("MYSQL")
        adapter3 = DatabaseAdapterFactory.get_adapter("mysql")
        
        assert all(isinstance(a, MySQLAdapter) for a in [adapter1, adapter2, adapter3])
    
    def test_unsupported_database(self):
        """测试不支持的数据库类型"""
        with pytest.raises(ValueError, match="不支持的数据库类型"):
            DatabaseAdapterFactory.get_adapter("mongodb")
    
    def test_get_supported_types(self):
        """测试获取支持的数据库类型列表"""
        supported = DatabaseAdapterFactory.get_supported_types()
        assert "mysql" in supported
        assert "postgresql" in supported
        assert "sqlite" in supported
    
    def test_is_supported(self):
        """测试检查数据库类型是否支持"""
        assert DatabaseAdapterFactory.is_supported("mysql")
        assert DatabaseAdapterFactory.is_supported("PostgreSQL")
        assert not DatabaseAdapterFactory.is_supported("mongodb")


class TestMySQLAdapter:
    """测试MySQL适配器"""
    
    def test_connection_string_with_auth(self):
        """测试带认证的连接字符串"""
        adapter = MySQLAdapter()
        config = {
            'url': 'localhost:3306/testdb',
            'username': 'root',
            'password': 'password123'
        }
        conn_str = adapter.get_connection_string(config)
        assert conn_str == "mysql+pymysql://root:password123@localhost:3306/testdb"
    
    def test_connection_string_without_auth(self):
        """测试不带认证的连接字符串"""
        adapter = MySQLAdapter()
        config = {
            'url': 'localhost:3306/testdb',
            'username': '',
            'password': ''
        }
        conn_str = adapter.get_connection_string(config)
        assert conn_str == "mysql+pymysql://localhost:3306/testdb"
    
    def test_format_identifier(self):
        """测试标识符格式化"""
        adapter = MySQLAdapter()
        assert adapter.format_identifier("table_name") == "`table_name`"
        assert adapter.format_identifier("column name") == "`column name`"


class TestPostgreSQLAdapter:
    """测试PostgreSQL适配器"""
    
    def test_connection_string_with_auth(self):
        """测试带认证的连接字符串"""
        adapter = PostgreSQLAdapter()
        config = {
            'url': 'localhost:5432/testdb',
            'username': 'postgres',
            'password': 'password123'
        }
        conn_str = adapter.get_connection_string(config)
        assert conn_str == "postgresql+psycopg2://postgres:password123@localhost:5432/testdb"
    
    def test_format_identifier(self):
        """测试标识符格式化"""
        adapter = PostgreSQLAdapter()
        assert adapter.format_identifier("table_name") == '"table_name"'
        assert adapter.format_identifier("Column Name") == '"Column Name"'


class TestSQLiteAdapter:
    """测试SQLite适配器"""
    
    def test_connection_string(self):
        """测试连接字符串"""
        adapter = SQLiteAdapter()
        config = {
            'url': 'sqlite:///data/test.db'
        }
        conn_str = adapter.get_connection_string(config)
        assert conn_str == "sqlite:///data/test.db"
    
    def test_connect_args(self):
        """测试连接参数"""
        adapter = SQLiteAdapter()
        connect_args = adapter.get_connect_args()
        assert connect_args == {"check_same_thread": False}
    
    def test_format_identifier(self):
        """测试标识符格式化"""
        adapter = SQLiteAdapter()
        assert adapter.format_identifier("table_name") == '"table_name"'


class TestAdapterRegistration:
    """测试适配器注册功能"""
    
    def test_register_custom_adapter(self):
        """测试注册自定义适配器"""
        from backend.services.database_adapters.base import DatabaseAdapter
        
        class CustomAdapter(DatabaseAdapter):
            def get_connection_string(self, config):
                return "custom://connection"
            
            def get_driver_name(self):
                return "custom"
            
            def get_connect_args(self):
                return {}
            
            def format_identifier(self, name):
                return f"[{name}]"
            
            def get_db_type(self):
                return "custom"
        
        # 注册自定义适配器
        DatabaseAdapterFactory.register_adapter("custom", CustomAdapter)
        
        # 验证可以获取
        adapter = DatabaseAdapterFactory.get_adapter("custom")
        assert isinstance(adapter, CustomAdapter)
        assert adapter.get_db_type() == "custom"
        
        # 清理（避免影响其他测试）
        DatabaseAdapterFactory._adapters.pop("custom", None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
