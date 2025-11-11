"""
常用报表模型
"""
from sqlalchemy import Column, String, Text
from .base import Base, TimestampMixin


class SavedReport(Base, TimestampMixin):
    """常用报表表"""
    __tablename__ = "saved_reports"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    query_plan = Column(Text, nullable=False)  # JSON: 包含SQL和MCP工具调用
    chart_config = Column(Text, nullable=False)  # JSON
    original_query = Column(Text, nullable=True)
    data_source_ids = Column(Text, nullable=False)  # JSON array: 数据库和MCP Server ID

    def __repr__(self):
        return f"<SavedReport(id={self.id}, name={self.name})>"
