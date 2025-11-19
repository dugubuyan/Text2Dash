"""
数据源管理器
统一管理数据库和MCP Server数据源，支持并行查询和数据组合
"""
import os
import sqlite3
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from .database_connector import DatabaseConnector, QueryResult, get_database_connector
from .mcp_connector import MCPConnector, MCPResult, get_mcp_connector
from .dto import QueryPlan, SQLQuery, MCPCall, DataMetadata
from ..utils.logger import get_logger

logger = get_logger(__name__)


class CombinedData:
    """组合后的数据"""
    def __init__(self, data: List[Dict[str, Any]], columns: List[str]):
        self.data = data
        self.columns = columns


class DataSourceManager:
    """数据源管理器类"""
    
    def __init__(
        self,
        db_connector: Optional[DatabaseConnector] = None,
        mcp_connector: Optional[MCPConnector] = None,
        temp_db_path: Optional[str] = None
    ):
        """
        初始化数据源管理器
        
        Args:
            db_connector: 数据库连接器实例，如果为None则使用全局实例
            mcp_connector: MCP连接器实例，如果为None则使用全局实例
            temp_db_path: 临时SQLite数据库路径，如果为None则使用默认路径
        """
        self.db = db_connector or get_database_connector()
        self.mcp = mcp_connector or get_mcp_connector()
        
        # 设置临时数据库路径
        if temp_db_path:
            self.temp_db_path = temp_db_path
        else:
            # 默认路径：./data/temp_data.db
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)
            self.temp_db_path = str(data_dir / "temp_data.db")
        
        # 存储最近一次创建的临时表信息
        self._last_temp_table_info = {}
        
        logger.info(f"数据源管理器初始化完成: temp_db_path={self.temp_db_path}")

    async def execute_query_plan(
        self,
        query_plan: QueryPlan
    ) -> CombinedData:
        """
        执行查询计划，并行查询所有数据源
        1. 并行执行数据库查询和MCP工具调用
        2. 验证MCP返回数据是表格形式
        3. 将MCP数据写入临时表
        4. 执行组合SQL查询
        
        Args:
            query_plan: 查询计划对象，包含SQL查询和MCP工具调用
            
        Returns:
            CombinedData对象，包含组合后的数据
            
        Raises:
            ValueError: 如果MCP数据格式不正确
            Exception: 如果查询执行失败
        """
        try:
            logger.info(
                f"开始执行查询计划: "
                f"sql_queries={len(query_plan.sql_queries)}, "
                f"mcp_calls={len(query_plan.mcp_calls)}, "
                f"needs_combination={query_plan.needs_combination}"
            )
            
            # 如果有多个SQL查询，需要顺序执行（因为后续查询可能依赖前面的结果）
            if len(query_plan.sql_queries) > 1:
                logger.info("检测到多个SQL查询，将顺序执行并创建临时表")
                db_results = []
                
                # 创建临时数据库连接
                conn = sqlite3.connect(self.temp_db_path)
                cursor = conn.cursor()
                
                try:
                    for sql_query in query_plan.sql_queries:
                        # 执行查询
                        result = await self._execute_sql_query(sql_query)
                        db_results.append(result)
                        
                        # 将结果创建为临时表，供后续查询使用
                        table_name = sql_query.source_alias
                        if result.data:
                            self._create_table_from_data(
                                cursor=cursor,
                                table_name=table_name,
                                data=result.data,
                                columns=result.columns
                            )
                            self._insert_data_to_table(
                                cursor=cursor,
                                table_name=table_name,
                                data=result.data,
                                columns=result.columns
                            )
                            conn.commit()
                            logger.info(f"创建中间临时表: {table_name}, rows={len(result.data)}")
                    
                    conn.close()
                except Exception as e:
                    conn.close()
                    raise
                
                # 并行执行MCP任务
                mcp_tasks = [self._execute_mcp_call(mcp_call) for mcp_call in query_plan.mcp_calls]
                if mcp_tasks:
                    mcp_task_results = await asyncio.gather(*mcp_tasks, return_exceptions=True)
                else:
                    mcp_task_results = []
                
                # 处理MCP结果
                errors = []
                mcp_results = []
                for i, result in enumerate(mcp_task_results):
                    if isinstance(result, Exception):
                        errors.append(str(result))
                        logger.error(f"MCP任务{i}失败: {result}")
                    elif isinstance(result, MCPResult):
                        if not self.mcp.validate_tool_response(result.data):
                            error_msg = (
                                f"MCP工具返回的数据格式不正确，必须是表格形式（list[dict]）: "
                                f"tool={result.tool_name}"
                            )
                            errors.append(error_msg)
                            logger.error(error_msg)
                        else:
                            mcp_results.append(result)
            else:
                # 单个查询或只有MCP调用，可以并行执行
                # 创建并行任务列表
                tasks = []
                
                # 添加数据库查询任务
                for sql_query in query_plan.sql_queries:
                    task = self._execute_sql_query(sql_query)
                    tasks.append(task)
                
                # 添加MCP工具调用任务
                for mcp_call in query_plan.mcp_calls:
                    task = self._execute_mcp_call(mcp_call)
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 检查是否有错误
                errors = []
                db_results = []
                mcp_results = []
                
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        errors.append(str(result))
                        logger.error(f"查询任务{i}失败: {result}")
                    elif isinstance(result, QueryResult):
                        db_results.append(result)
                    elif isinstance(result, MCPResult):
                        # 验证MCP数据格式
                        if not self.mcp.validate_tool_response(result.data):
                            error_msg = (
                                f"MCP工具返回的数据格式不正确，必须是表格形式（list[dict]）: "
                                f"tool={result.tool_name}"
                            )
                            errors.append(error_msg)
                            logger.error(error_msg)
                        else:
                            mcp_results.append(result)
            
            # 如果有错误，抛出异常
            if errors:
                raise Exception(f"查询执行失败: {'; '.join(errors)}")
            
            logger.info(
                f"并行查询完成: db_results={len(db_results)}, "
                f"mcp_results={len(mcp_results)}"
            )
            
            # 如果不需要组合，直接返回第一个结果
            if not query_plan.needs_combination:
                if db_results:
                    result = db_results[0]
                    return CombinedData(data=result.data, columns=result.columns)
                elif mcp_results:
                    result = mcp_results[0]
                    return CombinedData(data=result.data, columns=result.metadata.columns)
                else:
                    return CombinedData(data=[], columns=[])
            
            # 需要组合：创建临时表
            temp_table_mapping, temp_table_info = await self.create_temp_tables(
                mcp_results=mcp_results,
                db_results=db_results,
                sql_queries=query_plan.sql_queries,
                mcp_calls=query_plan.mcp_calls
            )
            
            logger.info(f"临时表创建完成: {list(temp_table_mapping.keys())}")
            
            # 将临时表信息存储到实例变量中，供后续使用
            self._last_temp_table_info = temp_table_info
            
            # 返回临时表映射信息，供后续组合使用
            # 注意：实际组合需要调用combine_data_with_sql方法
            return CombinedData(data=[], columns=[])
        
        except Exception as e:
            logger.error(
                f"执行查询计划失败",
                extra={
                    "query_plan": query_plan.dict(),
                    "error": str(e)
                }
            )
            raise
    
    async def _execute_sql_query(self, sql_query: SQLQuery) -> QueryResult:
        """
        执行单个SQL查询
        
        Args:
            sql_query: SQL查询对象
            
        Returns:
            QueryResult对象
        """
        logger.info(
            f"执行SQL查询: db_config_id={sql_query.db_config_id}, "
            f"alias={sql_query.source_alias}"
        )
        logger.debug(f"SQL语句:\n{sql_query.sql}")
        return await self.db.execute_query(
            db_config_id=sql_query.db_config_id,
            sql=sql_query.sql,
            session_temp_db_path=self.temp_db_path
        )
    
    async def _execute_mcp_call(self, mcp_call: MCPCall) -> MCPResult:
        """
        执行单个MCP工具调用
        
        Args:
            mcp_call: MCP工具调用对象
            
        Returns:
            MCPResult对象
        """
        logger.info(
            f"执行MCP工具调用: mcp_config_id={mcp_call.mcp_config_id}, "
            f"tool={mcp_call.tool_name}, alias={mcp_call.source_alias}"
        )
        return await self.mcp.call_tool(
            mcp_config_id=mcp_call.mcp_config_id,
            tool_name=mcp_call.tool_name,
            parameters=mcp_call.parameters
        )

    async def create_temp_tables(
        self,
        mcp_results: List[MCPResult],
        db_results: List[QueryResult],
        sql_queries: List[SQLQuery],
        mcp_calls: List[MCPCall]
    ) -> Tuple[Dict[str, str], Dict[str, Any]]:
        """
        在临时SQLite数据库中创建临时表
        将数据库查询结果和MCP数据写入临时表
        
        Args:
            mcp_results: MCP工具调用结果列表
            db_results: 数据库查询结果列表
            sql_queries: SQL查询列表（用于获取source_alias）
            mcp_calls: MCP调用列表（用于获取source_alias）
            
        Returns:
            元组 (table_mapping, temp_table_info)
            - table_mapping: 表名映射字典 {source_alias: table_name}
            - temp_table_info: 临时表信息字典 {table_name: {columns, source, row_count}}
        """
        try:
            # 创建或连接到临时数据库
            conn = sqlite3.connect(self.temp_db_path)
            cursor = conn.cursor()
            
            table_mapping = {}
            temp_table_info = {}
            
            # 处理数据库查询结果
            for i, (result, sql_query) in enumerate(zip(db_results, sql_queries)):
                table_name = f"temp_{sql_query.source_alias}"
                table_mapping[sql_query.source_alias] = table_name
                
                # 如果没有数据，仍然创建空表（避免组合SQL报错）
                if not result.data:
                    logger.warning(
                        f"数据库查询结果为空: {sql_query.source_alias}, "
                        f"columns={result.columns}，将创建空表"
                    )
                
                # 创建表
                logger.debug(
                    f"准备创建表: {table_name}, "
                    f"data_rows={len(result.data)}, "
                    f"columns={result.columns}"
                )
                self._create_table_from_data(
                    cursor=cursor,
                    table_name=table_name,
                    data=result.data if result.data else [],
                    columns=result.columns
                )
                
                # 插入数据（如果有数据）
                if result.data:
                    self._insert_data_to_table(
                        cursor=cursor,
                        table_name=table_name,
                        data=result.data,
                        columns=result.columns
                    )
                
                # 收集表信息
                column_types = {}
                if result.data:
                    first_row = result.data[0]
                    for col in result.columns:
                        value = first_row.get(col)
                        if value is None:
                            column_types[col] = "TEXT"
                        elif isinstance(value, bool):
                            column_types[col] = "INTEGER"
                        elif isinstance(value, int):
                            column_types[col] = "INTEGER"
                        elif isinstance(value, float):
                            column_types[col] = "REAL"
                        else:
                            column_types[col] = "TEXT"
                else:
                    # 如果没有数据，所有列类型默认为TEXT
                    column_types = {col: "TEXT" for col in result.columns}
                
                temp_table_info[table_name] = {
                    "columns": column_types,
                    "source": sql_query.source_alias,
                    "row_count": len(result.data)
                }
                
                logger.info(
                    f"创建临时表: {table_name}, rows={len(result.data)}, "
                    f"columns={len(result.columns)}"
                )
            
            # 处理MCP结果
            for i, (result, mcp_call) in enumerate(zip(mcp_results, mcp_calls)):
                table_name = f"temp_{mcp_call.source_alias}"
                table_mapping[mcp_call.source_alias] = table_name
                
                # 如果没有数据，仍然创建空表（避免组合SQL报错）
                if not result.data:
                    logger.warning(f"MCP工具返回数据为空: {mcp_call.source_alias}，将创建空表")
                
                # 获取列名
                if result.data:
                    columns = result.metadata.columns if result.metadata else list(result.data[0].keys())
                else:
                    # 如果没有数据，尝试从metadata获取列名
                    columns = result.metadata.columns if result.metadata else []
                
                logger.debug(
                    f"准备创建MCP表: {table_name}, "
                    f"data_rows={len(result.data)}, "
                    f"columns={columns}"
                )
                
                # 创建表
                self._create_table_from_data(
                    cursor=cursor,
                    table_name=table_name,
                    data=result.data if result.data else [],
                    columns=columns
                )
                
                # 插入数据（如果有数据）
                if result.data:
                    self._insert_data_to_table(
                        cursor=cursor,
                        table_name=table_name,
                        data=result.data,
                        columns=columns
                    )
                
                # 收集表信息
                column_types = {}
                if result.data:
                    first_row = result.data[0]
                    for col in columns:
                        value = first_row.get(col)
                        if value is None:
                            column_types[col] = "TEXT"
                        elif isinstance(value, bool):
                            column_types[col] = "INTEGER"
                        elif isinstance(value, int):
                            column_types[col] = "INTEGER"
                        elif isinstance(value, float):
                            column_types[col] = "REAL"
                        else:
                            column_types[col] = "TEXT"
                else:
                    # 如果没有数据，所有列类型默认为TEXT
                    column_types = {col: "TEXT" for col in columns}
                
                temp_table_info[table_name] = {
                    "columns": column_types,
                    "source": mcp_call.source_alias,
                    "row_count": len(result.data)
                }
                
                logger.info(
                    f"创建临时表: {table_name}, rows={len(result.data)}, "
                    f"columns={len(columns)}"
                )
            
            # 提交事务
            conn.commit()
            conn.close()
            
            logger.info(f"所有临时表创建完成: {list(table_mapping.keys())}")
            
            return table_mapping, temp_table_info
        
        except Exception as e:
            logger.error(
                f"创建临时表失败",
                extra={
                    "temp_db_path": self.temp_db_path,
                    "error": str(e)
                }
            )
            raise
    
    def _create_table_from_data(
        self,
        cursor: sqlite3.Cursor,
        table_name: str,
        data: List[Dict[str, Any]],
        columns: List[str]
    ):
        """
        根据数据创建表
        
        Args:
            cursor: SQLite游标
            table_name: 表名
            data: 数据列表
            columns: 列名列表
        """
        # 删除已存在的表
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        # 推断列类型
        column_types = {}
        if data:
            first_row = data[0]
            for col in columns:
                value = first_row.get(col)
                
                # 如果第一行是None，尝试找到非None的值
                if value is None:
                    for row in data:
                        value = row.get(col)
                        if value is not None:
                            break
                
                # 推断SQLite类型
                if value is None:
                    column_types[col] = "TEXT"
                elif isinstance(value, bool):
                    column_types[col] = "INTEGER"
                elif isinstance(value, int):
                    column_types[col] = "INTEGER"
                elif isinstance(value, float):
                    column_types[col] = "REAL"
                else:
                    column_types[col] = "TEXT"
        else:
            # 如果没有数据，所有列类型设为TEXT
            column_types = {col: "TEXT" for col in columns}
        
        # 检查是否有列
        if not columns:
            logger.error(f"无法创建表 {table_name}：没有列定义")
            raise Exception(f"无法创建表 {table_name}：没有列定义")
        
        # 构建CREATE TABLE语句
        # 使用方括号包裹列名（SQLite 支持，可以处理特殊字符）
        column_defs = [f"[{col}] {column_types[col]}" for col in columns]
        create_sql = f"CREATE TABLE {table_name} ({', '.join(column_defs)})"
        
        logger.debug(f"创建表SQL: {create_sql}")
        logger.debug(f"列名列表: {columns}")
        logger.debug(f"列类型: {column_types}")
        
        try:
            cursor.execute(create_sql)
            logger.info(f"成功创建表: {table_name}, 列数: {len(columns)}")
        except sqlite3.OperationalError as e:
            logger.error(
                f"创建表失败: {table_name}, "
                f"列名: {columns}, "
                f"SQL: {create_sql}, "
                f"错误: {e}"
            )
            raise
    
    def _insert_data_to_table(
        self,
        cursor: sqlite3.Cursor,
        table_name: str,
        data: List[Dict[str, Any]],
        columns: List[str]
    ):
        """
        将数据插入表
        
        Args:
            cursor: SQLite游标
            table_name: 表名
            data: 数据列表
            columns: 列名列表
        """
        if not data:
            return
        
        # 构建INSERT语句
        placeholders = ', '.join(['?' for _ in columns])
        insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        
        # 准备数据
        rows = []
        for row_dict in data:
            row = [row_dict.get(col) for col in columns]
            rows.append(row)
        
        # 批量插入
        cursor.executemany(insert_sql, rows)
        logger.debug(f"插入数据: {table_name}, rows={len(rows)}")
    
    def get_last_temp_table_info(self) -> Dict[str, Any]:
        """
        获取最近一次创建的临时表信息
        
        Returns:
            临时表信息字典 {table_name: {columns, source, row_count}}
        """
        return self._last_temp_table_info
    
    def cleanup_temp_tables(self):
        """
        清理临时表和临时数据库
        """
        try:
            if os.path.exists(self.temp_db_path):
                os.remove(self.temp_db_path)
                logger.info(f"清理临时数据库: {self.temp_db_path}")
            # 清理缓存的表信息
            self._last_temp_table_info = {}
        except Exception as e:
            logger.error(
                f"清理临时数据库失败",
                extra={
                    "temp_db_path": self.temp_db_path,
                    "error": str(e)
                }
            )

    async def combine_data_with_sql(
        self,
        combination_sql: str
    ) -> CombinedData:
        """
        使用SQL语句组合临时表中的数据
        支持：JOIN、UNION、聚合等所有SQL操作
        
        Args:
            combination_sql: LLM生成的组合SQL语句（必须是SELECT语句）
            
        Returns:
            CombinedData对象，包含组合后的数据
            
        Raises:
            Exception: 如果SQL执行失败
        """
        try:
            logger.info(f"执行组合SQL: {combination_sql[:100]}...")
            
            # 连接到临时数据库
            conn = sqlite3.connect(self.temp_db_path)
            cursor = conn.cursor()
            
            # 执行组合SQL（只能访问临时表）
            cursor.execute(combination_sql)
            
            # 获取列名
            columns = [desc[0] for desc in cursor.description]
            
            # 获取数据
            rows = cursor.fetchall()
            data = [dict(zip(columns, row)) for row in rows]
            
            conn.close()
            
            logger.info(
                f"组合SQL执行成功: rows={len(data)}, columns={len(columns)}"
            )
            
            return CombinedData(data=data, columns=columns)
        
        except Exception as e:
            logger.error(
                f"执行组合SQL失败",
                extra={
                    "sql": combination_sql,
                    "temp_db_path": self.temp_db_path,
                    "error": str(e)
                }
            )
            raise

    def get_combined_metadata(self, combined_data: CombinedData) -> DataMetadata:
        """
        提取组合后数据的元信息
        
        Args:
            combined_data: 组合后的数据对象
            
        Returns:
            DataMetadata对象，包含列名、列类型和行数
        """
        # 获取列名
        columns = combined_data.columns
        
        # 获取行数
        row_count = len(combined_data.data)
        
        # 推断列类型
        column_types = {}
        if row_count > 0:
            # 从第一行数据推断类型
            first_row = combined_data.data[0]
            for col in columns:
                value = first_row.get(col)
                
                # 如果第一行是None，尝试找到非None的值
                if value is None:
                    for row in combined_data.data:
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
            f"提取组合数据元信息: columns={len(columns)}, "
            f"row_count={row_count}"
        )
        
        return DataMetadata(
            columns=columns,
            column_types=column_types,
            row_count=row_count
        )
    
    # ============ Session 临时表管理方法 ============
    
    def create_session_temp_table(
        self,
        session_id: str,
        interaction_num: int,
        data: List[Dict[str, Any]],
        columns: Optional[List[str]] = None
    ) -> str:
        """创建 session 级临时表并保存数据"""
        if not data:
            logger.warning("数据为空，不创建临时表")
            return None
        
        # 替换 session_id 中的特殊字符，避免 SQL 语法错误
        safe_session_id = session_id.replace('-', '_')
        table_name = f"session_{safe_session_id}_interaction_{interaction_num}"
        
        if not columns:
            columns = list(data[0].keys())
        
        try:
            conn = sqlite3.connect(self.temp_db_path)
            cursor = conn.cursor()
            
            # 检查表是否已存在
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            if cursor.fetchone():
                cursor.execute(f"DROP TABLE {table_name}")
            
            # 推断列类型并创建表
            column_defs = []
            for col in columns:
                value = data[0].get(col)
                if value is None:
                    col_type = "TEXT"
                elif isinstance(value, bool):
                    col_type = "INTEGER"
                elif isinstance(value, int):
                    col_type = "INTEGER"
                elif isinstance(value, float):
                    col_type = "REAL"
                else:
                    col_type = "TEXT"
                column_defs.append(f"{col} {col_type}")
            
            create_sql = f"CREATE TABLE {table_name} ({', '.join(column_defs)})"
            cursor.execute(create_sql)
            
            # 插入数据
            placeholders = ', '.join(['?' for _ in columns])
            insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
            rows = [[row_dict.get(col) for col in columns] for row_dict in data]
            cursor.executemany(insert_sql, rows)
            
            conn.commit()
            conn.close()
            
            logger.info(f"创建 session 临时表: {table_name}, rows={len(data)}, columns={len(columns)}")
            return table_name
            
        except Exception as e:
            logger.error(f"创建 session 临时表失败: {table_name}, error={str(e)}", exc_info=True)
            raise
    
    def query_session_temp_table(
        self,
        table_name: str,
        limit: Optional[int] = None,
        offset: Optional[int] = 0
    ) -> List[Dict[str, Any]]:
        """从 session 临时表查询数据"""
        try:
            conn = sqlite3.connect(self.temp_db_path)
            cursor = conn.cursor()
            
            sql = f"SELECT * FROM {table_name}"
            if limit:
                sql += f" LIMIT {limit} OFFSET {offset}"
            
            cursor.execute(sql)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            data = [dict(zip(columns, row)) for row in rows]
            
            conn.close()
            logger.debug(f"查询临时表: {table_name}, rows={len(data)}")
            return data
            
        except Exception as e:
            logger.error(f"查询临时表失败: {table_name}, error={str(e)}", exc_info=True)
            return []
    
    def get_temp_table_schema(self, table_name: str) -> Optional[Dict[str, Any]]:
        """获取临时表的 schema 信息"""
        try:
            conn = sqlite3.connect(self.temp_db_path)
            cursor = conn.cursor()
            
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            if not cursor.fetchone():
                conn.close()
                return None
            
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns_info = cursor.fetchall()
            columns = [{"name": col[1], "type": col[2]} for col in columns_info]
            
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            
            conn.close()
            return {"columns": columns, "row_count": row_count}
            
        except Exception as e:
            logger.error(f"获取临时表 schema 失败: {table_name}, error={str(e)}", exc_info=True)
            return None
    
    def drop_session_temp_tables(self, session_id: str) -> int:
        """删除指定 session 的所有临时表"""
        try:
            conn = sqlite3.connect(self.temp_db_path)
            cursor = conn.cursor()
            
            # 替换 session_id 中的特殊字符，与创建时保持一致
            safe_session_id = session_id.replace('-', '_')
            pattern = f"session_{safe_session_id}_%"
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '{pattern}'")
            tables = cursor.fetchall()
            
            count = 0
            for (table_name,) in tables:
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                count += 1
                logger.debug(f"删除临时表: {table_name}")
            
            conn.commit()
            conn.close()
            
            if count > 0:
                logger.info(f"删除 session 临时表: session_id={session_id}, count={count}")
            return count
            
        except Exception as e:
            logger.error(f"删除 session 临时表失败: session_id={session_id}, error={str(e)}", exc_info=True)
            return 0
    
    def list_session_temp_tables(self, session_id: str) -> List[str]:
        """列出指定 session 的所有临时表"""
        try:
            conn = sqlite3.connect(self.temp_db_path)
            cursor = conn.cursor()
            
            # 替换 session_id 中的特殊字符，与创建时保持一致
            safe_session_id = session_id.replace('-', '_')
            pattern = f"session_{safe_session_id}_%"
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '{pattern}' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            return tables
            
        except Exception as e:
            logger.error(f"列出 session 临时表失败: session_id={session_id}, error={str(e)}", exc_info=True)
            return []


# 全局数据源管理器实例
_data_source_manager = None


def get_data_source_manager() -> DataSourceManager:
    """获取全局数据源管理器实例"""
    global _data_source_manager
    if _data_source_manager is None:
        _data_source_manager = DataSourceManager()
    return _data_source_manager
