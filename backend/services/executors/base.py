"""
执行器基类
"""
import uuid
import asyncio
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from ..report_service import ReportService, ReportResult


class BaseExecutor:
    """执行器基类"""
    
    def __init__(self, report_service: 'ReportService'):
        """
        初始化执行器
        
        Args:
            report_service: ReportService 实例
        """
        self.report_service = report_service
        self.llm = report_service.llm
        self.data_source = report_service.data_source
        self.session = report_service.session
        self.filter = report_service.filter
        self.db = report_service.db
    
    async def execute(self, **kwargs) -> 'ReportResult':
        """
        执行报表生成
        
        Args:
            **kwargs: 执行参数
        
        Returns:
            ReportResult 对象
        
        Raises:
            NotImplementedError: 子类必须实现此方法
        """
        raise NotImplementedError("子类必须实现 execute 方法")
    
    # ============ 通用辅助方法 ============
    
    async def handle_no_match(self, query, session_id, query_plan, data_source_ids, model):
        """处理无法匹配数据源的情况"""
        from ..report_service import ReportResult
        from ..dto import DataMetadata
        
        interaction_id = str(uuid.uuid4())
        
        asyncio.create_task(
            self.report_service._save_session_async(
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
        
        return ReportResult(
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
    
    async def combine_data(self, query, model, combined_data, query_plan=None):
        """
        组合数据
        
        Args:
            query: 用户查询
            model: LLM模型
            combined_data: 组合后的数据
            query_plan: 查询计划（可选），如果提供且包含combination_strategy则直接使用
        
        Returns:
            组合后的数据
        """
        from ...utils.logger import get_logger
        logger = get_logger(__name__)
        
        # 调用 LLM 生成组合 SQL
        logger.info("调用LLM生成组合SQL")
        
        # 优先使用最近创建的临时表信息（避免竞态条件）
        temp_table_info = self.data_source.get_last_temp_table_info()
        
        # 如果没有缓存的信息，则从数据库查询（兜底）
        if not temp_table_info:
            temp_table_info = await self.report_service._get_temp_table_info()
        
        combination_sql = await self.llm.generate_combination_sql(
            query=query,
            temp_table_info=temp_table_info,
            model=model
        )
        
        return await self.data_source.combine_data_with_sql(
            combination_sql=combination_sql
        )
    
    async def apply_filters(self, combined_data, data_source_ids):
        """应用敏感信息过滤"""
        return await self.report_service._apply_filters_to_combined_data(
            combined_data=combined_data,
            data_source_ids=data_source_ids
        )
