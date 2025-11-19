"""
临时表查询执行器 - 处理基于临时表的简单查询（如图表配置修改）
"""
import uuid
import asyncio
from typing import List

from .base import BaseExecutor
from ..dto import DataMetadata
from ..data_source_manager import CombinedData
from ..report_utils import build_sql_display, replace_placeholders_in_summary


class TempTableQueryExecutor(BaseExecutor):
    """临时表查询执行器"""
    
    async def execute(
        self,
        query: str,
        session_id: str,
        data_source_ids: List[str],
        model: str,
        **kwargs
    ):
        """
        执行临时表查询流程
        
        这个执行器用于处理只需要查询临时表的场景，比如：
        - 修改图表配置（x轴改为名字而不是id）
        - 对已有数据进行简单的筛选、排序
        - 不需要重新查询源数据库
        
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
        
        # 获取 session 临时表信息
        session_temp_tables = await self.report_service._get_session_temp_tables_info(session_id)
        
        if not session_temp_tables:
            # 如果没有临时表，降级到完整查询
            logger.warning("没有找到临时表，降级到完整查询")
            from .full_query import FullQueryExecutor
            executor = FullQueryExecutor(self.report_service)
            return await executor.execute(
                query=query,
                session_id=session_id,
                data_source_ids=data_source_ids,
                model=model
            )
        
        # 调用LLM生成查询计划（只针对临时表）
        # 注意：query 应该是智能路由提供的 refined_query，已包含完整意图
        query_plan = await self.llm.generate_query_plan(
            query=query,
            db_schemas={},  # 不提供原始数据库schema
            mcp_tools={},   # 不提供MCP工具
            model=model,
            session_temp_tables=session_temp_tables
        )
        
        logger.info(
            f"临时表查询计划生成完成: "
            f"sql_queries={len(query_plan.sql_queries)}"
        )
        
        # 执行查询计划
        combined_data = await self.data_source.execute_query_plan(query_plan)
        
        # 应用敏感信息过滤
        filtered_data = await self.report_service._apply_filters_to_combined_data(
            combined_data=combined_data,
            data_source_ids=data_source_ids
        )
        
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
        
        # 保存到会话（不创建新的临时表，因为数据来自已有临时表）
        interaction_id = str(uuid.uuid4())
        sql_display = build_sql_display(query_plan)
        
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
                temp_table_name=None  # 不创建新临时表
            )
        )
        
        logger.info(f"临时表查询完成: interaction_id={interaction_id}")
        
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
