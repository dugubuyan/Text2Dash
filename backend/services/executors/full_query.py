"""
完整查询执行器 - 执行完整的查询流程（查询新数据+生成图表）
"""
import uuid
import asyncio
from typing import List

from .base import BaseExecutor
from ..dto import DataMetadata
from ..data_source_manager import CombinedData
from ..report_utils import build_sql_display, replace_placeholders_in_summary, should_create_temp_table


class FullQueryExecutor(BaseExecutor):
    """完整查询执行器"""
    
    async def execute(
        self,
        query: str,
        session_id: str,
        data_source_ids: List[str],
        model: str,
        **kwargs
    ):
        """
        执行完整查询流程
        
        这是原有的完整逻辑，包括：
        1. 生成查询计划
        2. 执行查询
        3. 组合数据
        4. 过滤敏感信息
        5. 生成图表
        6. 保存会话
        
        Args:
            query: 用户查询
            session_id: 会话ID
            data_source_ids: 数据源ID列表
            model: 使用的模型
        
        Returns:
            ReportResult 对象
        """
        from ..report_service import ReportResult
        from ...utils.logger import get_logger
        
        logger = get_logger(__name__)
        
        # 获取数据源schema信息和 session 临时表信息
        db_schemas, mcp_tools = await self.report_service._get_data_source_info(data_source_ids)
        session_temp_tables = await self.report_service._get_session_temp_tables_info(session_id)
        
        # 调用LLM生成查询计划
        # 注意：query 应该是智能路由提供的 refined_query，已包含完整意图
        query_plan = await self.llm.generate_query_plan(
            query=query,
            db_schemas=db_schemas,
            mcp_tools=mcp_tools,
            model=model,
            session_temp_tables=session_temp_tables
        )
        
        logger.info(
            f"查询计划生成完成: no_match={query_plan.no_data_source_match}, "
            f"sql_queries={len(query_plan.sql_queries)}, "
            f"mcp_calls={len(query_plan.mcp_calls)}"
        )
        
        # 检查是否无法匹配数据源
        if query_plan.no_data_source_match:
            return await self.handle_no_match(
                query, session_id, query_plan, data_source_ids, model
            )
        
        # 执行查询计划
        combined_data = await self.data_source.execute_query_plan(query_plan)
        
        # 如果需要组合数据
        if query_plan.needs_combination:
            combined_data = await self.combine_data(query, model, combined_data, query_plan)
        
        # 应用敏感信息过滤
        filtered_data = await self.apply_filters(combined_data, data_source_ids)
        
        # 获取数据元信息
        metadata = self.data_source.get_combined_metadata(
            CombinedData(data=filtered_data, columns=combined_data.columns)
        )
        
        # 提取SQL查询用于缓存key（使用第一个SQL查询）
        sql_for_cache = None
        if query_plan.sql_queries:
            sql_for_cache = query_plan.sql_queries[0].sql
        
        # 生成图表配置和总结
        chart_suggestion = await self.llm.analyze_data_and_suggest_chart(
            query=query,
            metadata=metadata,
            model=model,
            sql_query=sql_for_cache
        )
        
        # 替换占位符
        final_summary = replace_placeholders_in_summary(
            chart_suggestion.summary,
            filtered_data
        )
        
        # 清理临时表
        if query_plan.needs_combination:
            self.data_source.cleanup_temp_tables()
        
        # 保存到会话
        interaction_id = str(uuid.uuid4())
        sql_display = build_sql_display(query_plan)
        
        # 判断是否需要创建临时表
        need_temp_table = should_create_temp_table(query_plan)
        
        if need_temp_table:
            interaction_num = await self.report_service._get_next_interaction_num(session_id)
            temp_table_name = self.data_source.create_session_temp_table(
                session_id=session_id,
                interaction_num=interaction_num,
                data=filtered_data,
                columns=combined_data.columns
            )
        else:
            temp_table_name = None
        
        # 异步保存会话
        asyncio.create_task(
            self.report_service._save_session_async(
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
        
        return ReportResult(
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
