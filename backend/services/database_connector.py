"""
数据库连接器
管理数据库连接和查询执行
"""
import os
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.pool import QueuePool
from sqlalchemy.engine import Engine
from contextlib import contextmanager

from ..database import get_database
from ..models.database_config import DatabaseConfig
from .encryption_service import get_encryption_service
from .dto import DataMetadata
from ..utils.logger import get_logger
from .database_adapters import DatabaseAdapterFactory

logger = get_logger(__name__)


class ConnectionTestResult:
    """连接测试结果"""
    def __init__(self, success: bool, message: str, error: Optional[str] = None):
        self.success = success
        self.message = message
        self.error = error


class QueryResult:
    """查询结果"""
    def __init__(self, data: List[Dict[str, Any]], columns: List[str]):
        self.data = data
        self.columns = columns


class SchemaInfo:
    """数据库Schema信息"""
    def __init__(self, tables: Dict[str, List[Dict[str, str]]]):
        """
        Args:
            tables: 表名到列信息的映射
                   例如: {"users": [{"name": "id", "type": "INTEGER"}, ...]}
        """
        self.tables = tables


class DatabaseConnector:
    """数据库连接器类"""
    
    def __init__(self):
        """初始化数据库连接器"""
        self.connections: Dict[str, Engine] = {}
        self.encryption_service = get_encryption_service()
        self.config_db = get_database()
    
    def _get_connection_string(self, db_config: DatabaseConfig) -> str:
        """
        构建数据库连接字符串
        
        Args:
            db_config: 数据库配置对象
            
        Returns:
            数据库连接字符串
        """
        # 解密密码
        password = ""
        if db_config.encrypted_password:
            try:
                password = self.encryption_service.decrypt(db_config.encrypted_password)
            except Exception as e:
                logger.error(f"解密数据库密码失败: {e}")
                raise ValueError("无法解密数据库密码")
        
        # 使用适配器构建连接字符串
        try:
            adapter = DatabaseAdapterFactory.get_adapter(db_config.type)
            config_dict = {
                'url': db_config.url,
                'username': db_config.username,
                'password': password
            }
            return adapter.get_connection_string(config_dict)
        except ValueError as e:
            logger.error(f"获取数据库适配器失败: {e}")
            raise
    
    def _get_or_create_connection(self, db_config_id: str) -> Engine:
        """
        获取或创建数据库连接
        
        Args:
            db_config_id: 数据库配置ID
            
        Returns:
            SQLAlchemy Engine对象
        """
        # 如果连接已存在，直接返回
        if db_config_id in self.connections:
            return self.connections[db_config_id]
        
        # 从配置数据库获取配置
        with self.config_db.get_session() as session:
            db_config = session.query(DatabaseConfig).filter_by(id=db_config_id).first()
            if not db_config:
                raise ValueError(f"数据库配置不存在: {db_config_id}")
            
            # 构建连接字符串
            connection_string = self._get_connection_string(db_config)
            
            # 获取适配器的连接参数
            adapter = DatabaseAdapterFactory.get_adapter(db_config.type)
            connect_args = adapter.get_connect_args()
            
            # 创建连接
            engine = create_engine(
                connection_string,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                connect_args=connect_args
            )
            
            # 缓存连接
            self.connections[db_config_id] = engine
            logger.info(f"创建数据库连接: {db_config.name} ({db_config.type})")
            
            return engine
    
    def _split_sql_statements(self, sql: str) -> List[str]:
        """
        将多个SQL语句分割成单独的语句
        
        Args:
            sql: 可能包含多个语句的SQL字符串
            
        Returns:
            SQL语句列表
        """
        # 简单的分割逻辑：按分号分割，并过滤空语句
        statements = []
        for stmt in sql.split(';'):
            stmt = stmt.strip()
            if stmt:
                statements.append(stmt)
        return statements
    
    async def execute_query(
        self,
        db_config_id: str,
        sql: str,
        session_temp_db_path: Optional[str] = None
    ) -> QueryResult:
        """
        执行SQL查询并返回结果
        支持执行多个SQL语句（用分号分隔），返回最后一个SELECT语句的结果
        
        Args:
            db_config_id: 数据库配置ID，特殊值 "__session__" 表示查询 session 临时表
            sql: SQL查询语句（可以包含多个语句，用分号分隔）
            session_temp_db_path: session 临时数据库路径（当 db_config_id="__session__" 时需要）
            
        Returns:
            QueryResult对象，包含查询结果和列名
            
        Raises:
            ValueError: 如果数据库配置不存在
            Exception: 如果SQL执行失败
        """
        # 特殊处理：查询 session 临时表
        if db_config_id == "__session__":
            if not session_temp_db_path:
                raise ValueError("查询 session 临时表时必须提供 session_temp_db_path")
            
            logger.debug(
                f"准备执行 Session 临时表查询:\n"
                f"  临时数据库: {session_temp_db_path}\n"
                f"  SQL: {sql[:200]}{'...' if len(sql) > 200 else ''}"
            )
            
            import sqlite3
            conn = sqlite3.connect(session_temp_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            try:
                cursor.execute(sql)
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                data = [dict(row) for row in rows]
                
                logger.info(
                    f"Session 临时表查询成功: rows={len(data)}, columns={len(columns)}"
                )
                
                return QueryResult(data=data, columns=columns)
            finally:
                conn.close()
        
        # 获取数据库配置信息用于日志
        with self.config_db.get_session() as session:
            db_config = session.query(DatabaseConfig).filter_by(id=db_config_id).first()
            if not db_config:
                raise ValueError(f"数据库配置不存在: {db_config_id}")
            
            logger.debug(
                f"准备执行SQL查询:\n"
                f"  数据库: {db_config.name} ({db_config.type})\n"
                f"  配置ID: {db_config_id}\n"
                f"  连接URL: {db_config.url}\n"
                f"  SQL: {sql[:200]}{'...' if len(sql) > 200 else ''}"
            )
        
        try:
            engine = self._get_or_create_connection(db_config_id)
            
            # 记录实际的数据库URL（隐藏密码）
            db_url = str(engine.url)
            if '@' in db_url:
                # 隐藏密码
                parts = db_url.split('@')
                if ':' in parts[0]:
                    user_pass = parts[0].split(':')
                    db_url = f"{user_pass[0]}:****@{parts[1]}"
            logger.debug(f"数据库连接URL: {db_url}")
            
            # 分割SQL语句
            statements = self._split_sql_statements(sql)
            logger.debug(f"检测到 {len(statements)} 个SQL语句")
            
            # 如果只有一个语句，直接执行
            if len(statements) == 1:
                with engine.connect() as connection:
                    result = connection.execute(text(statements[0]))
                    
                    # 获取列名
                    columns = list(result.keys())
                    
                    # 获取数据
                    rows = result.fetchall()
                    data = [dict(zip(columns, row)) for row in rows]
                    
                    logger.info(
                        f"SQL查询成功: db_config_id={db_config_id}, "
                        f"rows={len(data)}, columns={len(columns)}"
                    )
                    logger.debug(f"返回的列: {columns}")
                    
                    return QueryResult(data=data, columns=columns)
            
            # 如果有多个语句，逐个执行
            # 对于非SELECT语句，只执行不返回结果
            # 对于SELECT语句，保存结果
            last_result = None
            with engine.connect() as connection:
                for i, stmt in enumerate(statements):
                    logger.debug(f"执行语句 {i+1}/{len(statements)}: {stmt[:100]}...")
                    result = connection.execute(text(stmt))
                    
                    # 检查是否是SELECT语句（有返回结果）
                    if result.returns_rows:
                        columns = list(result.keys())
                        rows = result.fetchall()
                        data = [dict(zip(columns, row)) for row in rows]
                        last_result = QueryResult(data=data, columns=columns)
                        logger.debug(f"语句 {i+1} 返回 {len(data)} 行")
                    else:
                        logger.debug(f"语句 {i+1} 执行完成（无返回结果）")
            
            # 返回最后一个有结果的查询
            if last_result is None:
                # 如果没有SELECT语句，返回空结果
                logger.warning("没有SELECT语句返回结果，返回空结果集")
                return QueryResult(data=[], columns=[])
            
            logger.info(
                f"多语句SQL查询成功: db_config_id={db_config_id}, "
                f"statements={len(statements)}, "
                f"rows={len(last_result.data)}, columns={len(last_result.columns)}"
            )
            
            return last_result
        
        except Exception as e:
            logger.error(
                f"SQL执行失败:\n"
                f"  数据库: {db_config.name}\n"
                f"  配置ID: {db_config_id}\n"
                f"  SQL: {sql}\n"
                f"  错误: {str(e)}"
            )
            raise
    
    async def get_schema_info(self, db_config_id: str) -> SchemaInfo:
        """
        获取数据库schema信息（表名、列名、类型）
        
        Args:
            db_config_id: 数据库配置ID
            
        Returns:
            SchemaInfo对象，包含所有表和列的信息
        """
        try:
            engine = self._get_or_create_connection(db_config_id)
            inspector = inspect(engine)
            
            tables = {}
            for table_name in inspector.get_table_names():
                columns = []
                for column in inspector.get_columns(table_name):
                    columns.append({
                        "name": column["name"],
                        "type": str(column["type"])
                    })
                tables[table_name] = columns
            
            logger.info(
                f"获取Schema信息成功: db_config_id={db_config_id}, "
                f"tables={len(tables)}"
            )
            
            return SchemaInfo(tables=tables)
        
        except Exception as e:
            logger.error(
                f"获取Schema信息失败",
                extra={
                    "db_config_id": db_config_id,
                    "error": str(e)
                }
            )
            raise
    
    async def test_connection(self, db_config: DatabaseConfig) -> ConnectionTestResult:
        """
        测试数据库连接
        
        Args:
            db_config: 数据库配置对象
            
        Returns:
            ConnectionTestResult对象，包含测试结果
        """
        try:
            # 构建连接字符串
            connection_string = self._get_connection_string(db_config)
            
            # 获取适配器的连接参数
            adapter = DatabaseAdapterFactory.get_adapter(db_config.type)
            connect_args = adapter.get_connect_args()
            
            # 创建临时连接
            engine = create_engine(
                connection_string,
                connect_args=connect_args
            )
            
            # 测试连接
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            
            logger.info(f"数据库连接测试成功: {db_config.name}")
            return ConnectionTestResult(
                success=True,
                message=f"连接成功: {db_config.name}"
            )
        
        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"数据库连接测试失败",
                extra={
                    "db_config": db_config.name,
                    "type": db_config.type,
                    "error": error_msg
                }
            )
            return ConnectionTestResult(
                success=False,
                message="连接失败",
                error=error_msg
            )
    
    def close_connection(self, db_config_id: str):
        """
        关闭指定的数据库连接
        
        Args:
            db_config_id: 数据库配置ID
        """
        if db_config_id in self.connections:
            self.connections[db_config_id].dispose()
            del self.connections[db_config_id]
            logger.info(f"关闭数据库连接: {db_config_id}")
    
    def close_all_connections(self):
        """关闭所有数据库连接"""
        for db_config_id in list(self.connections.keys()):
            self.close_connection(db_config_id)
        logger.info("关闭所有数据库连接")
    
    def get_data_metadata(self, query_result: QueryResult) -> DataMetadata:
        """
        提取数据元信息：列名、数据类型、行数
        
        Args:
            query_result: 查询结果对象
            
        Returns:
            DataMetadata对象，包含列名、列类型和行数
        """
        # 获取列名
        columns = query_result.columns
        
        # 获取行数
        row_count = len(query_result.data)
        
        # 推断列类型
        column_types = {}
        if row_count > 0:
            # 从第一行数据推断类型
            first_row = query_result.data[0]
            for col in columns:
                value = first_row.get(col)
                if value is None:
                    # 如果第一行是None，尝试找到非None的值
                    for row in query_result.data:
                        value = row.get(col)
                        if value is not None:
                            break
                
                # 推断Python类型
                if value is None:
                    column_types[col] = "NULL"
                elif isinstance(value, bool):
                    column_types[col] = "BOOLEAN"
                elif isinstance(value, int):
                    column_types[col] = "INTEGER"
                elif isinstance(value, float):
                    column_types[col] = "FLOAT"
                elif isinstance(value, str):
                    column_types[col] = "TEXT"
                else:
                    column_types[col] = str(type(value).__name__)
        else:
            # 如果没有数据，所有列类型设为UNKNOWN
            column_types = {col: "UNKNOWN" for col in columns}
        
        logger.info(
            f"提取数据元信息: columns={len(columns)}, "
            f"row_count={row_count}"
        )
        
        return DataMetadata(
            columns=columns,
            column_types=column_types,
            row_count=row_count
        )


# 全局数据库连接器实例
_db_connector = None


def get_database_connector() -> DatabaseConnector:
    """获取全局数据库连接器实例"""
    global _db_connector
    if _db_connector is None:
        _db_connector = DatabaseConnector()
    return _db_connector
