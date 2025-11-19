"""
复用数据执行器 - 复用上次查询的数据，重新生成图表
"""
import uuid
import asyncio
from typing import List, Optional

from .base import BaseExecutor
from ..dto import DataMetadata
from ..data_source_manager import CombinedData
from ..report_utils import replace_placeholders_in_summary


class ReuseDataExecutor(BaseExecutor):
    """复用数据执行器"""
    
    async def execute(
        self,
        query: str,
        session_id: str,
        data_source_ids: List[str],
        model: str,
        **kwargs
    ):
        """
        复用上次查询的数据，重新生成图表
        
        这个执行器用于处理只需要改变图表配置的场景，比如：
        - "换成柱状图"
        - "改成饼图"
        - "x轴改为名字"
        
        不需要重新查询数据，只需要：
        1. 从上次交互获取数据
        2. 调用LLM生成新的图表配置
        3. 保存新的交互记录
        
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
        
        # 步骤1: 获取上次交互的数据
        last_interaction = await self.session.get_last_interaction(session_id)
        
        if not last_interaction or not last_interaction.get("temp_table_name"):
            # 如果没有上次数据，降级到完整查询
            logger.warning("没有找到上次数据，降级到完整查询")
            from .full_query import FullQueryExecutor
            executor = FullQueryExecutor(self.report_service)
            return await executor.execute(
                query=query,
                session_id=session_id,
                data_source_ids=data_source_ids,
                model=model
            )
        
        # 步骤2: 从临时表读取数据
        temp_table_name = last_interaction["temp_table_name"]
        
        try:
            # 查询临时表获取所有数据
            data = self.data_source.query_session_temp_table(temp_table_name)
            schema = self.data_source.get_temp_table_schema(temp_table_name)
            
            # 从 schema 中提取列名列表
            # schema["columns"] 是 [{"name": "col1", "type": "TEXT"}, ...] 格式
            columns = [col["name"] for col in schema["columns"]]
            
            logger.info(f"从临时表复用数据: {temp_table_name}, rows={len(data)}, columns={len(columns)}")
            
        except Exception as e:
            logger.error(f"读取临时表失败: {temp_table_name}, {e}")
            # 降级到完整查询
            from .full_query import FullQueryExecutor
            executor = FullQueryExecutor(self.report_service)
            return await executor.execute(
                query=query,
                session_id=session_id,
                data_source_ids=data_source_ids,
                model=model
            )
        
        # 步骤3: 应用敏感信息过滤
        filtered_data = await self.report_service._apply_filters_to_combined_data(
            combined_data=CombinedData(data=data, columns=columns),
            data_source_ids=data_source_ids
        )
        
        # 步骤4: 获取数据元信息
        metadata = self.data_source.get_combined_metadata(
            CombinedData(data=filtered_data, columns=columns)
        )
        
        # 步骤5: 调用LLM生成新的图表配置
        # 重要：设置 use_cache=False，强制重新生成图表
        # 原因：reuse_data_regenerate_chart 的语义就是"重新生成"，应该跳过缓存
        # 这样可以确保每次图表调整请求都会生成新的配置，符合用户预期
        chart_suggestion = await self.llm.analyze_data_and_suggest_chart(
            query=query,
            metadata=metadata,
            model=model,
            sql_query=f"-- REUSE: {temp_table_name}",
            use_cache=False  # 跳过缓存，强制调用LLM
        )
        
        # 替换占位符
        final_summary = replace_placeholders_in_summary(
            chart_suggestion.summary,
            filtered_data
        )
        
        logger.info(f"新图表配置生成完成: type={chart_suggestion.chart_type}")
        
        # 步骤6: 获取原始查询计划（用于保存报表）
        # 从上次交互中获取原始的 query_plan
        original_query_plan = last_interaction.get("query_plan")
        if original_query_plan:
            logger.debug(f"从上次交互获取原始查询计划: {original_query_plan}")
        else:
            logger.warning("上次交互没有查询计划，将使用None")
        
        # 步骤7: 保存到会话（不创建新临时表，复用原有临时表）
        interaction_id = str(uuid.uuid4())
        
        # 异步保存会话
        asyncio.create_task(
            self.report_service._save_session_async(
                session_id=session_id,
                interaction_id=interaction_id,
                query=query,
                sql_display=f"-- 复用临时表: {temp_table_name}",
                query_plan=original_query_plan,  # 使用原始查询计划
                chart_config=chart_suggestion.chart_config,
                summary=final_summary,
                data_source_ids=data_source_ids,
                data_snapshot=filtered_data[:10],
                temp_table_name=temp_table_name  # 复用原有临时表
            )
        )
        
        logger.info(f"复用数据完成: interaction_id={interaction_id}")
        
        return ReportResult(
            session_id=session_id,
            interaction_id=interaction_id,
            sql_query=f"-- 复用临时表: {temp_table_name}",
            query_plan=original_query_plan,  # 返回原始查询计划
            chart_config=chart_suggestion.chart_config,
            summary=final_summary,
            data=filtered_data,
            metadata=metadata,
            original_query=query,
            data_source_ids=data_source_ids,
            model=model
        )
