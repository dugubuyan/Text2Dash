"""
对话执行器 - 处理直接对话（不需要查询数据或生成图表）
"""
import uuid
import asyncio
from typing import Optional, List

from .base import BaseExecutor
from ..dto import DataMetadata


class ConversationExecutor(BaseExecutor):
    """对话执行器"""
    
    async def execute(
        self,
        query: str,
        session_id: str,
        response: str,
        suggestions: Optional[List[str]],
        model: str,
        **kwargs
    ):
        """
        执行直接对话
        
        Args:
            query: 用户查询
            session_id: 会话ID
            response: 直接回复内容
            suggestions: 给用户的建议列表
            model: 使用的模型
        
        Returns:
            ReportResult 对象
        """
        from ..report_service import ReportResult
        
        interaction_id = str(uuid.uuid4())
        
        # 确保response不为None
        if response is None:
            response = ""
        
        # 如果有建议，添加到回复中
        if suggestions:
            response += "\n\n建议：\n" + "\n".join([f"- {s}" for s in suggestions])
        
        # 异步保存到会话历史
        asyncio.create_task(
            self.session.add_interaction_with_id(
                interaction_id=interaction_id,
                session_id=session_id,
                user_query=query,
                summary=response
            )
        )
        
        return ReportResult(
            session_id=session_id,
            interaction_id=interaction_id,
            sql_query=None,
            query_plan=None,
            chart_config={"type": "text"},
            summary=response,
            data=[],
            metadata=DataMetadata(columns=[], column_types={}, row_count=0),
            original_query=query,
            data_source_ids=[],
            model=model
        )
