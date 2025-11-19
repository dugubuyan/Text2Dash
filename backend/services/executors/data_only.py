"""
仅数据执行器 - 只查询数据，不生成图表
"""
import uuid
import asyncio
from typing import List

from .base import BaseExecutor
from ..dto import DataMetadata
from ..data_source_manager import CombinedData
from ..report_utils import build_sql_display


class DataOnlyExecutor(BaseExecutor):
    """仅数据执行器"""
    
    async def execute(
        self,
        query: str,
        session_id: str,
        data_source_ids: List[str],
        model: str,
        **kwargs
    ):
        """
        只查询数据，不生成图表
        
        这个执行器用于处理只需要数据的场景，比如：
        - "给我看看销售数据"
        - "导出用户列表"
        - "查询订单记录"
        
        流程：
        1. 生成查询计划
        2. 执行查询
        3. 组合数据（如需要）
        4. 过滤敏感信息
        5. 返回数据（不生成图表配置）
        
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
        from ..report_utils import should_create_temp_table
        
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
            f"查询计划生成完成（仅数据）: "
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
        
        # 生成简单的摘要（不调用LLM）
        summary = f"查询完成，共 {len(filtered_data)} 条记录"
        
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
                chart_config={"type": "table"},  # 默认表格展示
                summary=summary,
                data_source_ids=data_source_ids,
                data_snapshot=filtered_data[:10],
                temp_table_name=temp_table_name
            )
        )
        
        logger.info(f"仅数据查询完成: interaction_id={interaction_id}")
        
        return ReportResult(
            session_id=session_id,
            interaction_id=interaction_id,
            sql_query=sql_display,
            query_plan=query_plan,
            chart_config={"type": "table"},  # 默认表格展示
            summary=summary,
            data=filtered_data,
            metadata=metadata,
            original_query=query,
            data_source_ids=data_source_ids,
            model=model
        )
