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
from .report_utils import build_sql_display, replace_placeholders_in_summary
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
        
        # 初始化执行器
        from .executors import (
            ConversationExecutor,
            FullQueryExecutor,
            TempTableQueryExecutor,
            ReuseDataExecutor,
            DataOnlyExecutor
        )
        
        self.executors = {
            'direct_conversation': ConversationExecutor(self),
            'clarify_and_guide': ConversationExecutor(self),
            'query_new_data_with_chart': FullQueryExecutor(self),
            'reuse_data_regenerate_chart': ReuseDataExecutor(self),
            'query_temp_table_with_chart': TempTableQueryExecutor(self),
            'query_data_only': DataOnlyExecutor(self),
        }
        
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
            
            # 步骤1: 获取所有交互历史（用于智能路由）
            all_interactions = await self.session.get_all_interactions(session_id)
            logger.debug(f"获取交互历史: {len(all_interactions)} 条")
            
            # 步骤2: 获取数据源概要（用于智能路由）
            data_source_summary = await self._get_data_source_summary(data_source_ids)
            
            # 步骤3: 智能路由决策
            execution_plan = await self.llm.smart_route(
                query=query,
                all_interactions=all_interactions,
                data_source_summary=data_source_summary,
                model=model
            )
            
            logger.info(f"智能路由决策: action={execution_plan.action}")
            
            # 步骤4: 使用执行器执行
            executor = self.executors.get(execution_plan.action)
            
            # 确定使用的查询文本：优先使用 refined_query，否则使用原始 query
            effective_query = execution_plan.refined_query or query
            
            if executor:
                # 使用执行器执行
                return await executor.execute(
                    query=effective_query,
                    original_query=query,  # 保留原始查询用于日志和显示
                    session_id=session_id,
                    data_source_ids=data_source_ids,
                    model=model,
                    response=execution_plan.direct_response,
                    suggestions=execution_plan.suggestions
                )
            
            # 步骤5: 如果没有对应的执行器，使用完整查询流程（兜底）
            logger.warning(f"未找到执行器: {execution_plan.action}，使用完整查询流程")
            executor = self.executors['query_new_data_with_chart']
            return await executor.execute(
                query=effective_query,
                original_query=query,
                session_id=session_id,
                data_source_ids=data_source_ids,
                model=model
            )
            
            # 原有的完整查询逻辑已迁移到 FullQueryExecutor
            
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
                        # 如果配置了使用schema描述文件，则使用文件内容
                        if db_config.use_schema_file and db_config.schema_description:
                            db_schemas[source_id] = {
                                "name": db_config.name,
                                "type": db_config.type,
                                "schema_description": db_config.schema_description
                            }
                            logger.debug(f"使用schema描述文件: {source_id}")
                        else:
                            # 否则从数据库获取schema信息
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
    
    async def _get_data_source_summary(
        self,
        data_source_ids: List[str]
    ) -> Dict[str, Any]:
        """
        获取数据源概要信息（用于智能路由）
        
        Args:
            data_source_ids: 数据源ID列表
        
        Returns:
            数据源概要字典 {"databases": [...], "mcp_servers": [...]}
        """
        summary = {"databases": [], "mcp_servers": []}
        
        with self.db.get_session() as session:
            from ..models.database_config import DatabaseConfig
            from ..models.mcp_server_config import MCPServerConfig
            
            for source_id in data_source_ids:
                # 检查是否是数据库
                db_config = session.query(DatabaseConfig).filter(
                    DatabaseConfig.id == source_id
                ).first()
                
                if db_config:
                    # 优先使用 schema_summary（如果已生成）
                    if db_config.schema_summary:
                        description = db_config.schema_summary
                    # 降级1：使用 schema_description 的前500字符
                    elif db_config.schema_description:
                        description = db_config.schema_description[:500] + "..."
                    # 降级2：使用表名列表
                    else:
                        try:
                            schema_info = await self.data_source.db.get_schema_info(source_id)
                            table_names = list(schema_info.tables.keys())
                            
                            if len(table_names) <= 15:
                                description = f"包含表：{', '.join(table_names)}"
                            else:
                                description = f"包含{len(table_names)}个表，主要有：{', '.join(table_names[:15])}等"
                        except:
                            description = f"{db_config.type}数据库"
                    
                    summary["databases"].append({
                        "id": db_config.id,
                        "name": db_config.name,
                        "description": description
                    })
                    continue
                
                # 检查是否是MCP服务器
                mcp_config = session.query(MCPServerConfig).filter(
                    MCPServerConfig.id == source_id
                ).first()
                
                if mcp_config:
                    summary["mcp_servers"].append({
                        "id": mcp_config.id,
                        "name": mcp_config.name,
                        "description": mcp_config.description or "MCP服务"
                    })
        
        return summary
    

    
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
            logger.debug(f"查询计划字典: {json.dumps(query_plan_dict, ensure_ascii=False)[:500]}")
            
            # 步骤2: 重建QueryPlan对象
            from .dto import SQLQuery, MCPCall
            
            sql_queries_data = query_plan_dict.get("sql_queries", [])
            mcp_calls_data = query_plan_dict.get("mcp_calls", [])
            
            logger.debug(f"SQL查询数量: {len(sql_queries_data)}, MCP调用数量: {len(mcp_calls_data)}")
            
            query_plan = QueryPlan(
                no_data_source_match=query_plan_dict.get("no_data_source_match", False),
                user_message=query_plan_dict.get("user_message"),
                sql_queries=[SQLQuery(**q) for q in sql_queries_data],
                mcp_calls=[MCPCall(**c) for c in mcp_calls_data],
                needs_combination=query_plan_dict.get("needs_combination", False),
                combination_strategy=query_plan_dict.get("combination_strategy")
            )
            
            # 步骤3: 执行查询计划
            combined_data = await self.data_source.execute_query_plan(query_plan)
            
            # 步骤4: 如果需要组合数据
            if query_plan.needs_combination:
                # 优先使用最近创建的临时表信息（避免竞态条件）
                temp_table_info = self.data_source.get_last_temp_table_info()
                
                # 如果没有缓存的信息，则从数据库查询（兜底）
                if not temp_table_info:
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
                final_summary = replace_placeholders_in_summary(
                    chart_suggestion.summary,
                    filtered_data
                )
                
                logger.info(f"LLM分析完成: type={chart_suggestion.chart_type}")
            else:
                # 不需要分析：直接使用保存的配置和summary
                final_chart_config = chart_config
                
                # 使用保存的summary并替换占位符
                if saved_report.summary:
                    final_summary = replace_placeholders_in_summary(
                        saved_report.summary,
                        filtered_data
                    )
                else:
                    # 如果没有保存summary，使用description作为后备
                    final_summary = saved_report.description or "常用报表执行结果"
                
                logger.info("使用保存的图表配置和summary（无LLM调用）")
            
            # 步骤8: 清理临时表
            if query_plan.needs_combination:
                self.data_source.cleanup_temp_tables()
                logger.debug("临时表清理完成")
            
            # 步骤9: 如果提供了session_id，异步保存到会话历史
            interaction_id = None
            if session_id:
                sql_display = build_sql_display(query_plan)
                
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
                sql_query=build_sql_display(query_plan),
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
