"""
报表生成服务
整合LLM、数据源管理器、过滤器和会话管理器，实现完整的报表生成流程
"""
import json
import uuid
import asyncio
from typing import Dict, List, Any, Optional

from .llm_service import LLMService
from .data_source_manager import DataSourceManager, CombinedData
from .filter_service import FilterService
from .session_manager import SessionManager
from .dto import QueryPlan, DataMetadata, ChartSuggestion
from ..database import Database
from ..models.saved_report import SavedReport
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ReportResult:
    """报表生成结果"""
    def __init__(
        self,
        session_id: str,
        interaction_id: str,
        sql_query: Optional[str],
        query_plan: Optional[Dict[str, Any]],
        chart_config: Optional[Dict[str, Any]],
        summary: str,
        data: List[Dict[str, Any]],
        metadata: DataMetadata,
        original_query: Optional[str] = None,
        data_source_ids: Optional[List[str]] = None,
        model: str = "gemini/gemini-2.0-flash"
    ):
        self.session_id = session_id
        self.interaction_id = interaction_id
        self.sql_query = sql_query
        self.query_plan = query_plan
        self.chart_config = chart_config
        self.summary = summary
        self.data = data
        self.metadata = metadata
        self.original_query = original_query
        self.data_source_ids = data_source_ids or []
        self.model = model


class ReportService:
    """报表生成服务类"""
    
    def __init__(
        self,
        llm_service: LLMService,
        data_source_manager: DataSourceManager,
        filter_service: FilterService,
        session_manager: SessionManager,
        database: Database
    ):
        """
        初始化报表生成服务
        
        Args:
            llm_service: LLM服务实例
            data_source_manager: 数据源管理器实例
            filter_service: 敏感信息过滤服务实例
            session_manager: 会话管理器实例
            database: 数据库实例
        """
        self.llm = llm_service
        self.data_source = data_source_manager
        self.filter = filter_service
        self.session = session_manager
        self.db = database
        
        logger.info("报表生成服务初始化完成")

    async def generate_report(
        self,
        query: str,
        model: str,
        session_id: str,
        data_source_ids: List[str]
    ) -> ReportResult:
        """
        主要报表生成流程
        
        完整流程：
        1. 获取会话上下文
        2. 调用LLM生成查询计划（SQL和/或MCP工具调用）
        3. 并行执行所有数据源查询
        4. 验证MCP数据格式（必须是表格形式）
        5. 如果需要组合：创建临时表，调用LLM生成组合SQL，执行组合查询
        6. 应用敏感信息过滤
        7. 获取数据元信息
        8. 调用LLM生成图表配置和总结
        9. 清理临时表
        10. 保存到会话历史
        
        Args:
            query: 用户的自然语言查询
            model: 使用的LLM模型
            session_id: 会话ID
            data_source_ids: 数据源ID列表（数据库和MCP Server）
        
        Returns:
            ReportResult对象，包含报表数据和配置
        
        Raises:
            Exception: 如果报表生成失败
        """
        try:
            logger.info(
                f"开始生成报表: query='{query[:50]}...', "
                f"model={model}, session_id={session_id}, "
                f"data_sources={len(data_source_ids)}"
            )
            
            # 步骤1: 获取会话上下文
            context = await self.session.get_context(session_id, limit=5)
            logger.debug(f"获取会话上下文: {len(context)} 条消息")
            
            # 步骤2: 获取数据源schema信息和 session 临时表信息
            db_schemas, mcp_tools = await self._get_data_source_info(data_source_ids)
            session_temp_tables = await self._get_session_temp_tables_info(session_id)
            
            # 步骤3: 调用LLM生成查询计划
            query_plan = await self.llm.generate_query_plan(
                query=query,
                db_schemas=db_schemas,
                mcp_tools=mcp_tools,
                context=context,
                model=model,
                session_temp_tables=session_temp_tables
            )
            
            logger.info(
                f"查询计划生成完成: no_match={query_plan.no_data_source_match}, "
                f"use_temp_table={query_plan.use_temp_table}, "
                f"temp_table={query_plan.temp_table_name}, "
                f"sql_queries={len(query_plan.sql_queries)}, "
                f"mcp_calls={len(query_plan.mcp_calls)}, "
                f"needs_combination={query_plan.needs_combination}"
            )
            
            # 检查是否使用临时表
            if query_plan.use_temp_table and query_plan.temp_table_name:
                # 直接从临时表查询数据
                logger.info(f"使用临时表: {query_plan.temp_table_name}")
                
                temp_data = self.data_source.query_session_temp_table(
                    table_name=query_plan.temp_table_name
                )
                
                if not temp_data:
                    raise Exception(f"临时表 {query_plan.temp_table_name} 不存在或为空")
                
                # 构建 CombinedData
                columns = list(temp_data[0].keys()) if temp_data else []
                combined_data = CombinedData(data=temp_data, columns=columns)
                
                # 跳过数据查询步骤，直接进入过滤和分析
                logger.info(f"从临时表获取数据: rows={len(temp_data)}, columns={len(columns)}")
                
                # 应用敏感信息过滤
                filtered_data = await self._apply_filters_to_combined_data(
                    combined_data=combined_data,
                    data_source_ids=data_source_ids
                )
                
                # 获取数据元信息
                metadata = self.data_source.get_combined_metadata(
                    CombinedData(data=filtered_data, columns=combined_data.columns)
                )
                
                # 调用LLM生成图表配置和总结
                chart_suggestion = await self.llm.analyze_data_and_suggest_chart(
                    query=query,
                    metadata=metadata,
                    model=model
                )
                
                final_summary = self._replace_placeholders_in_summary(
                    chart_suggestion.summary,
                    filtered_data
                )
                
                # 生成interaction_id
                interaction_id = str(uuid.uuid4())
                
                # 异步保存到会话历史
                asyncio.create_task(
                    self._save_session_async(
                        session_id=session_id,
                        interaction_id=interaction_id,
                        query=query,
                        sql_display=f"-- 使用临时表: {query_plan.temp_table_name}",
                        query_plan=query_plan.model_dump() if hasattr(query_plan, 'model_dump') else query_plan.dict(),
                        chart_config=chart_suggestion.chart_config,
                        summary=final_summary,
                        data_source_ids=data_source_ids,
                        data_snapshot=filtered_data[:10]
                    )
                )
                
                # 返回结果
                result = ReportResult(
                    session_id=session_id,
                    interaction_id=interaction_id,
                    sql_query=f"-- 使用临时表: {query_plan.temp_table_name}",
                    query_plan=query_plan,
                    chart_config=chart_suggestion.chart_config,
                    summary=final_summary,
                    data=filtered_data,
                    metadata=metadata,
                    original_query=query,
                    data_source_ids=data_source_ids,
                    model=model
                )
                
                logger.info(f"临时表查询完成: interaction_id={interaction_id}")
                return result
            
            # 检查是否无法匹配数据源
            if query_plan.no_data_source_match:
                # 返回友好提示，不执行查询
                logger.info(f"查询无法匹配数据源: {query_plan.user_message}")
                
                # 生成interaction_id
                interaction_id = str(uuid.uuid4())
                
                # 异步保存到会话历史
                asyncio.create_task(
                    self._save_session_async(
                        session_id=session_id,
                        interaction_id=interaction_id,
                        query=query,
                        sql_display="-- 无法匹配数据源",
                        query_plan=query_plan.model_dump() if hasattr(query_plan, 'model_dump') else query_plan.dict(),
                        chart_config={"type": "text"},
                        summary=query_plan.user_message or "无法找到相关数据",
                        data_source_ids=data_source_ids,
                        data_snapshot=[]
                    )
                )
                
                # 返回友好提示结果
                result = ReportResult(
                    session_id=session_id,
                    interaction_id=interaction_id,
                    sql_query=None,
                    query_plan=None,
                    chart_config={"type": "text"},
                    summary=query_plan.user_message or "无法找到相关数据",
                    data=[],
                    metadata=DataMetadata(columns=[], column_types={}, row_count=0),
                    original_query=query,
                    data_source_ids=data_source_ids,
                    model=model
                )
                
                logger.info(f"返回友好提示: {query_plan.user_message}")
                return result
            
            # 步骤4: 执行查询计划（并行执行所有数据源查询）
            combined_data = await self.data_source.execute_query_plan(query_plan)
            
            # 步骤5: 如果需要组合数据
            if query_plan.needs_combination:
                # 获取临时表信息
                temp_table_info = await self._get_temp_table_info()
                
                # 调用LLM生成组合SQL
                combination_sql = await self.llm.generate_combination_sql(
                    query=query,
                    temp_table_info=temp_table_info,
                    model=model
                )
                
                logger.info(f"组合SQL生成完成: {combination_sql[:100]}...")
                
                # 执行组合SQL
                combined_data = await self.data_source.combine_data_with_sql(
                    combination_sql=combination_sql
                )
                
                logger.info(f"数据组合完成: rows={len(combined_data.data)}")
            
            # 步骤6: 应用敏感信息过滤
            filtered_data = await self._apply_filters_to_combined_data(
                combined_data=combined_data,
                data_source_ids=data_source_ids
            )
            
            logger.info(f"敏感信息过滤完成: rows={len(filtered_data)}")
            
            # 步骤7: 获取数据元信息
            metadata = self.data_source.get_combined_metadata(
                CombinedData(data=filtered_data, columns=combined_data.columns)
            )
            
            logger.debug(
                f"数据元信息: columns={len(metadata.columns)}, "
                f"rows={metadata.row_count}"
            )
            
            # 步骤8: 调用LLM生成图表配置和总结
            chart_suggestion = await self.llm.analyze_data_and_suggest_chart(
                query=query,
                metadata=metadata,
                model=model
            )
            
            # 替换 summary 中的占位符（用于 text 类型）
            final_summary = self._replace_placeholders_in_summary(
                chart_suggestion.summary,
                filtered_data
            )
            
            logger.info(
                f"图表分析完成: type={chart_suggestion.chart_type}, "
                f"summary_length={len(final_summary)}"
            )
            
            # 步骤9: 清理临时表
            if query_plan.needs_combination:
                self.data_source.cleanup_temp_tables()
                logger.debug("临时表清理完成")
            
            # 步骤10: 保存完整数据到临时表并异步保存会话历史
            # 构建SQL查询字符串（用于显示）
            sql_display = self._build_sql_display(query_plan)
            
            # 生成interaction_id（用于返回）
            interaction_id = str(uuid.uuid4())
            
            # 保存完整数据到临时表
            interaction_num = await self._get_next_interaction_num(session_id)
            temp_table_name = self.data_source.create_session_temp_table(
                session_id=session_id,
                interaction_num=interaction_num,
                data=filtered_data,
                columns=combined_data.columns
            )
            
            logger.info(f"数据已保存到临时表: {temp_table_name}, rows={len(filtered_data)}")
            
            # 创建后台任务异步保存会话
            asyncio.create_task(
                self._save_session_async(
                    session_id=session_id,
                    interaction_id=interaction_id,
                    query=query,
                    sql_display=sql_display,
                    query_plan=query_plan.model_dump() if hasattr(query_plan, 'model_dump') else query_plan.dict(),
                    chart_config=chart_suggestion.chart_config,
                    summary=final_summary,
                    data_source_ids=data_source_ids,
                    data_snapshot=filtered_data[:10],
                    temp_table_name=temp_table_name
                )
            )
            
            logger.info(f"会话交互将异步保存: interaction_id={interaction_id}")
            
            # 构建返回结果
            result = ReportResult(
                session_id=session_id,
                interaction_id=interaction_id,
                sql_query=sql_display,
                query_plan=query_plan,
                chart_config=chart_suggestion.chart_config,
                summary=final_summary,
                data=filtered_data,
                metadata=metadata,
                original_query=query,
                data_source_ids=data_source_ids,
                model=model
            )
            
            logger.info(
                f"报表生成完成: session_id={session_id}, "
                f"interaction_id={interaction_id}, "
                f"data_rows={len(filtered_data)}"
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"报表生成失败",
                extra={
                    "query": query,
                    "session_id": session_id,
                    "model": model,
                    "error": str(e)
                },
                exc_info=True
            )
            raise Exception(f"报表生成失败: {str(e)}")
    
    async def _get_data_source_info(
        self,
        data_source_ids: List[str]
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """
        获取数据源信息（schema和工具描述）
        
        Args:
            data_source_ids: 数据源ID列表
        
        Returns:
            (db_schemas, mcp_tools) 元组
        """
        db_schemas = {}
        mcp_tools = {}
        
        # 从数据库获取配置信息
        with self.db.get_session() as session:
            from ..models.database_config import DatabaseConfig
            from ..models.mcp_server_config import MCPServerConfig
            
            for source_id in data_source_ids:
                # 尝试作为数据库配置
                db_config = session.query(DatabaseConfig).filter(
                    DatabaseConfig.id == source_id
                ).first()
                
                if db_config:
                    # 获取数据库schema
                    try:
                        schema_info = await self.data_source.db.get_schema_info(source_id)
                        db_schemas[source_id] = {
                            "name": db_config.name,
                            "type": db_config.type,
                            "tables": schema_info.tables
                        }
                        logger.debug(f"获取数据库schema: {source_id}")
                    except Exception as e:
                        logger.warning(f"获取数据库schema失败: {source_id}, {e}")
                    continue
                
                # 尝试作为MCP Server配置
                mcp_config = session.query(MCPServerConfig).filter(
                    MCPServerConfig.id == source_id
                ).first()
                
                if mcp_config:
                    # 获取MCP工具列表
                    try:
                        tools = await self.data_source.mcp.get_available_tools(source_id)
                        mcp_tools[source_id] = {
                            "name": mcp_config.name,
                            "tools": [
                                {
                                    "name": tool.name,
                                    "description": tool.description,
                                    "parameters": tool.parameters
                                }
                                for tool in tools
                            ]
                        }
                        logger.debug(f"获取MCP工具列表: {source_id}, tools={len(tools)}")
                    except Exception as e:
                        logger.warning(f"获取MCP工具列表失败: {source_id}, {e}")
        
        return db_schemas, mcp_tools
    
    async def _get_session_temp_tables_info(self, session_id: str) -> List[Dict[str, Any]]:
        """
        获取 session 的临时表信息
        
        Args:
            session_id: 会话ID
        
        Returns:
            临时表信息列表
        """
        temp_tables_info = []
        
        try:
            # 获取该 session 的所有临时表
            table_names = self.data_source.list_session_temp_tables(session_id)
            
            for table_name in table_names:
                # 获取表的 schema
                schema = self.data_source.get_temp_table_schema(table_name)
                if not schema:
                    continue
                
                # 从数据库获取对应的交互记录
                with self.db.get_session() as db_session:
                    from ..models.session import SessionInteraction
                    
                    interaction = db_session.query(SessionInteraction).filter(
                        SessionInteraction.temp_table_name == table_name
                    ).first()
                    
                    user_query = interaction.user_query if interaction else "Unknown"
                
                temp_tables_info.append({
                    "table_name": table_name,
                    "user_query": user_query,
                    "columns": schema["columns"],
                    "row_count": schema["row_count"]
                })
            
            logger.debug(f"获取 session 临时表信息: session_id={session_id}, count={len(temp_tables_info)}")
            
        except Exception as e:
            logger.error(f"获取 session 临时表信息失败: {e}", exc_info=True)
        
        return temp_tables_info
    
    async def _get_next_interaction_num(self, session_id: str) -> int:
        """
        获取下一个交互编号
        
        Args:
            session_id: 会话ID
        
        Returns:
            交互编号
        """
        with self.db.get_session() as db_session:
            from ..models.session import SessionInteraction
            
            count = db_session.query(SessionInteraction).filter(
                SessionInteraction.session_id == session_id
            ).count()
            
            return count + 1
    
    async def _get_temp_table_info(self) -> Dict[str, Any]:
        """
        获取临时表信息
        
        Returns:
            临时表信息字典 {table_name: {columns, types, source, row_count}}
        """
        import sqlite3
        
        temp_table_info = {}
        
        try:
            conn = sqlite3.connect(self.data_source.temp_db_path)
            cursor = conn.cursor()
            
            # 获取所有表名
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'temp_%'"
            )
            tables = cursor.fetchall()
            
            for (table_name,) in tables:
                # 获取表结构
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns_info = cursor.fetchall()
                
                columns = {}
                for col_info in columns_info:
                    col_name = col_info[1]
                    col_type = col_info[2]
                    columns[col_name] = col_type
                
                # 获取行数
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cursor.fetchone()[0]
                
                # 提取source_alias（去掉temp_前缀）
                source_alias = table_name.replace("temp_", "")
                
                temp_table_info[table_name] = {
                    "columns": columns,
                    "source": source_alias,
                    "row_count": row_count
                }
            
            conn.close()
            
            logger.debug(f"获取临时表信息: {list(temp_table_info.keys())}")
            
        except Exception as e:
            logger.error(f"获取临时表信息失败: {e}", exc_info=True)
        
        return temp_table_info
    
    async def _apply_filters_to_combined_data(
        self,
        combined_data: CombinedData,
        data_source_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        对组合后的数据应用敏感信息过滤
        
        Args:
            combined_data: 组合后的数据
            data_source_ids: 数据源ID列表
        
        Returns:
            过滤后的数据列表
        """
        filtered_data = combined_data.data
        
        # 对每个数据库配置应用过滤规则
        for source_id in data_source_ids:
            # 检查是否是数据库配置
            with self.db.get_session() as session:
                from ..models.database_config import DatabaseConfig
                
                db_config = session.query(DatabaseConfig).filter(
                    DatabaseConfig.id == source_id
                ).first()
                
                if db_config:
                    # 应用过滤规则
                    filtered_data = await self.filter.apply_filters(
                        data=filtered_data,
                        db_config_id=source_id
                    )
        
        return filtered_data
    
    async def _save_session_async(
        self,
        session_id: str,
        interaction_id: str,
        query: str,
        sql_display: str,
        query_plan: Optional[Dict[str, Any]],
        chart_config: Optional[Dict[str, Any]],
        summary: str,
        data_source_ids: List[str],
        data_snapshot: List[Dict[str, Any]],
        temp_table_name: Optional[str] = None
    ) -> None:
        """
        异步保存会话交互（后台任务）
        
        Args:
            session_id: 会话ID
            interaction_id: 交互ID
            query: 用户查询
            sql_display: SQL显示字符串
            query_plan: 查询计划（可选）
            chart_config: 图表配置（可选）
            summary: 总结
            data_source_ids: 数据源ID列表
            data_snapshot: 数据快照
            temp_table_name: 临时表名（可选）
        """
        try:
            # 保存交互
            await self.session.add_interaction_with_id(
                interaction_id=interaction_id,
                session_id=session_id,
                user_query=query,
                sql_query=sql_display,
                query_plan=query_plan,
                chart_config=chart_config,
                summary=summary,
                data_source_ids=data_source_ids,
                data_snapshot=data_snapshot,
                temp_table_name=temp_table_name
            )
            
            logger.info(f"会话交互已异步保存: interaction_id={interaction_id}, temp_table={temp_table_name}")
            
            # 检查是否需要压缩会话上下文
            await self.session.check_and_compress(session_id, self.llm)
            
        except Exception as e:
            logger.error(
                f"异步保存会话失败: interaction_id={interaction_id}, error={str(e)}",
                exc_info=True
            )
    
    def _build_sql_display(self, query_plan: QueryPlan) -> str:
        """
        构建用于显示的SQL查询字符串
        
        Args:
            query_plan: 查询计划
        
        Returns:
            SQL显示字符串
        """
        sql_parts = []
        
        # 添加SQL查询
        for i, sql_query in enumerate(query_plan.sql_queries, 1):
            sql_parts.append(f"-- 数据库查询 {i} ({sql_query.source_alias})")
            sql_parts.append(sql_query.sql)
            sql_parts.append("")
        
        # 添加MCP调用
        for i, mcp_call in enumerate(query_plan.mcp_calls, 1):
            sql_parts.append(f"-- MCP工具调用 {i} ({mcp_call.source_alias})")
            sql_parts.append(f"-- 工具: {mcp_call.tool_name}")
            sql_parts.append(f"-- 参数: {json.dumps(mcp_call.parameters, ensure_ascii=False)}")
            sql_parts.append("")
        
        return "\n".join(sql_parts)
    
    def _replace_placeholders_in_summary(
        self,
        summary: str,
        data: List[Dict[str, Any]]
    ) -> str:
        """
        替换 summary 中的数据占位符
        
        支持多种占位符格式：
        - {{DATA_PLACEHOLDER}}: 第一行第一列的值
        - {{DATA_PLACEHOLDER_X}}: 第一行第一列的值（通常是类别名）
        - {{DATA_PLACEHOLDER_1}}, {{DATA_PLACEHOLDER_2}}, ...: 第一行的第1、2、...列的值
        
        Args:
            summary: 包含占位符的摘要文本
            data: 数据列表
        
        Returns:
            替换后的摘要文本
        """
        import re
        
        if not summary or "{{DATA_PLACEHOLDER" not in summary:
            return summary
        
        # 如果数据为空，替换所有占位符为"无数据"
        if not data or not data[0]:
            result = re.sub(r'\{\{DATA_PLACEHOLDER[^}]*\}\}', '无数据', summary)
            logger.debug(f"数据为空，替换所有占位符: '{summary}' -> '{result}'")
            return result
        
        # 获取第一行数据
        first_row = data[0]
        columns = list(first_row.keys())
        
        # 格式化值的辅助函数
        def format_value(value):
            if value is None:
                return "无数据"
            if isinstance(value, (int, float)):
                return f"{value:,}"
            return str(value)
        
        result = summary
        
        # 查找所有占位符
        placeholders = re.findall(r'\{\{DATA_PLACEHOLDER[^}]*\}\}', summary)
        
        for placeholder in placeholders:
            # 提取占位符类型
            if placeholder == "{{DATA_PLACEHOLDER}}":
                # 默认占位符：取第一列的值
                value = first_row.get(columns[0]) if columns else None
                formatted_value = format_value(value)
                result = result.replace(placeholder, formatted_value)
                logger.debug(f"替换 {placeholder} -> {formatted_value} (列: {columns[0] if columns else 'N/A'})")
                
            elif placeholder == "{{DATA_PLACEHOLDER_X}}":
                # X轴占位符：取第一列的值（通常是类别名）
                value = first_row.get(columns[0]) if columns else None
                formatted_value = format_value(value)
                result = result.replace(placeholder, formatted_value)
                logger.debug(f"替换 {placeholder} -> {formatted_value} (列: {columns[0] if columns else 'N/A'})")
                
            else:
                # 带索引的占位符：{{DATA_PLACEHOLDER_1}}, {{DATA_PLACEHOLDER_2}}, ...
                match = re.match(r'\{\{DATA_PLACEHOLDER_(\d+)\}\}', placeholder)
                if match:
                    index = int(match.group(1)) - 1  # 转换为0-based索引
                    if 0 <= index < len(columns):
                        column_name = columns[index]
                        value = first_row.get(column_name)
                        formatted_value = format_value(value)
                        result = result.replace(placeholder, formatted_value)
                        logger.debug(f"替换 {placeholder} -> {formatted_value} (列: {column_name})")
                    else:
                        # 索引超出范围
                        result = result.replace(placeholder, "无数据")
                        logger.warning(f"占位符索引超出范围: {placeholder}, 列数: {len(columns)}")
        
        logger.debug(f"占位符替换完成: '{summary}' -> '{result}'")
        
        return result

    async def run_saved_report(
        self,
        report_id: str,
        with_analysis: bool,
        session_id: Optional[str] = None,
        model: Optional[str] = None
    ) -> ReportResult:
        """
        执行常用报表
        
        两种模式：
        - with_analysis=False: 直接执行查询+渲染（零LLM调用，最快）
        - with_analysis=True: 执行查询+调用LLM一次生成分析
        
        Args:
            report_id: 常用报表ID
            with_analysis: 是否需要分析功能
            session_id: 会话ID（可选，如果不提供则创建新会话）
            model: 使用的LLM模型（仅在with_analysis=True时需要）
        
        Returns:
            ReportResult对象，包含报表数据和配置
        
        Raises:
            Exception: 如果报表执行失败
        """
        try:
            logger.info(
                f"开始执行常用报表: report_id={report_id}, "
                f"with_analysis={with_analysis}, session_id={session_id}"
            )
            
            # 步骤1: 从数据库获取常用报表配置
            with self.db.get_session() as db_session:
                saved_report = db_session.query(SavedReport).filter(
                    SavedReport.id == report_id
                ).first()
                
                if not saved_report:
                    raise Exception(f"常用报表不存在: {report_id}")
                
                # 解析配置
                query_plan_dict = json.loads(saved_report.query_plan)
                chart_config = json.loads(saved_report.chart_config)
                data_source_ids = json.loads(saved_report.data_source_ids)
                original_query = saved_report.original_query
            
            logger.debug(
                f"常用报表配置加载完成: name={saved_report.name}, "
                f"data_sources={len(data_source_ids)}"
            )
            
            # 步骤2: 重建QueryPlan对象
            from .dto import SQLQuery, MCPCall
            
            query_plan = QueryPlan(
                no_data_source_match=query_plan_dict.get("no_data_source_match", False),
                user_message=query_plan_dict.get("user_message"),
                use_temp_table=query_plan_dict.get("use_temp_table", False),
                temp_table_name=query_plan_dict.get("temp_table_name"),
                sql_queries=[SQLQuery(**q) for q in query_plan_dict.get("sql_queries", [])],
                mcp_calls=[MCPCall(**c) for c in query_plan_dict.get("mcp_calls", [])],
                needs_combination=query_plan_dict.get("needs_combination", False),
                combination_strategy=query_plan_dict.get("combination_strategy")
            )
            
            # 步骤3: 执行查询计划
            combined_data = await self.data_source.execute_query_plan(query_plan)
            
            # 步骤4: 如果需要组合数据
            if query_plan.needs_combination:
                # 获取临时表信息
                temp_table_info = await self._get_temp_table_info()
                
                # 使用保存的组合策略或重新生成
                if query_plan.combination_strategy:
                    # 如果保存了组合SQL，直接使用
                    combination_sql = query_plan.combination_strategy
                else:
                    # 否则需要LLM生成（这种情况需要with_analysis=True）
                    if not with_analysis:
                        raise Exception("该报表需要数据组合但未保存组合SQL，请使用with_analysis=True模式")
                    
                    if not model:
                        model = self.llm.default_model
                    
                    combination_sql = await self.llm.generate_combination_sql(
                        query=original_query or "组合数据",
                        temp_table_info=temp_table_info,
                        model=model
                    )
                
                # 执行组合SQL
                combined_data = await self.data_source.combine_data_with_sql(
                    combination_sql=combination_sql
                )
                
                logger.info(f"数据组合完成: rows={len(combined_data.data)}")
            
            # 步骤5: 应用敏感信息过滤
            filtered_data = await self._apply_filters_to_combined_data(
                combined_data=combined_data,
                data_source_ids=data_source_ids
            )
            
            logger.info(f"敏感信息过滤完成: rows={len(filtered_data)}")
            
            # 步骤6: 获取数据元信息
            metadata = self.data_source.get_combined_metadata(
                CombinedData(data=filtered_data, columns=combined_data.columns)
            )
            
            # 步骤7: 处理图表配置和总结
            if with_analysis:
                # 需要分析：调用LLM生成新的分析和总结
                if not model:
                    model = self.llm.default_model
                
                chart_suggestion = await self.llm.analyze_data_and_suggest_chart(
                    query=original_query or "数据分析",
                    metadata=metadata,
                    model=model
                )
                
                # 使用新的图表配置和总结，并替换占位符
                final_chart_config = chart_suggestion.chart_config
                final_summary = self._replace_placeholders_in_summary(
                    chart_suggestion.summary,
                    filtered_data
                )
                
                logger.info(f"LLM分析完成: type={chart_suggestion.chart_type}")
            else:
                # 不需要分析：直接使用保存的配置
                final_chart_config = chart_config
                final_summary = saved_report.description or "常用报表执行结果"
                
                logger.info("使用保存的图表配置（无LLM调用）")
            
            # 步骤8: 清理临时表
            if query_plan.needs_combination:
                self.data_source.cleanup_temp_tables()
                logger.debug("临时表清理完成")
            
            # 步骤9: 如果提供了session_id，异步保存到会话历史
            interaction_id = None
            if session_id:
                sql_display = self._build_sql_display(query_plan)
                
                # 生成interaction_id
                interaction_id = str(uuid.uuid4())
                
                # 异步保存
                asyncio.create_task(
                    self._save_session_async(
                        session_id=session_id,
                        interaction_id=interaction_id,
                        query=f"执行常用报表: {saved_report.name}",
                        sql_display=sql_display,
                        query_plan=query_plan.model_dump() if hasattr(query_plan, 'model_dump') else query_plan.dict(),
                        chart_config=final_chart_config,
                        summary=final_summary,
                        data_source_ids=data_source_ids,
                        data_snapshot=filtered_data[:10]
                    )
                )
                
                logger.info(f"会话交互将异步保存: interaction_id={interaction_id}")
            
            # 构建返回结果
            result = ReportResult(
                session_id=session_id or "",
                interaction_id=interaction_id or "",
                sql_query=self._build_sql_display(query_plan),
                query_plan=query_plan,
                chart_config=final_chart_config,
                summary=final_summary,
                data=filtered_data,
                metadata=metadata,
                model=model or "gemini/gemini-2.0-flash"
            )
            
            # 添加缺失的字段用于响应
            result.original_query = original_query
            result.data_source_ids = data_source_ids
            
            logger.info(
                f"常用报表执行完成: report_id={report_id}, "
                f"with_analysis={with_analysis}, "
                f"data_rows={len(filtered_data)}"
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"常用报表执行失败",
                extra={
                    "report_id": report_id,
                    "with_analysis": with_analysis,
                    "session_id": session_id,
                    "error": str(e)
                },
                exc_info=True
            )
            raise Exception(f"常用报表执行失败: {str(e)}")


# 全局报表服务实例
_report_service = None


def get_report_service(
    llm_service: Optional[LLMService] = None,
    data_source_manager: Optional[DataSourceManager] = None,
    filter_service: Optional[FilterService] = None,
    session_manager: Optional[SessionManager] = None,
    database: Optional[Database] = None
) -> ReportService:
    """
    获取全局报表服务实例
    
    Args:
        llm_service: LLM服务实例（可选）
        data_source_manager: 数据源管理器实例（可选）
        filter_service: 过滤服务实例（可选）
        session_manager: 会话管理器实例（可选）
        database: 数据库实例（可选）
    
    Returns:
        ReportService实例
    """
    global _report_service
    
    if _report_service is None:
        # 如果没有提供依赖，使用默认实例
        if llm_service is None:
            llm_service = LLMService()
        
        if data_source_manager is None:
            from .data_source_manager import get_data_source_manager
            data_source_manager = get_data_source_manager()
        
        if database is None:
            from ..database import get_database
            database = get_database()
        
        if filter_service is None:
            filter_service = FilterService(database)
        
        if session_manager is None:
            session_manager = SessionManager(database)
        
        _report_service = ReportService(
            llm_service=llm_service,
            data_source_manager=data_source_manager,
            filter_service=filter_service,
            session_manager=session_manager,
            database=database
        )
    
    return _report_service
