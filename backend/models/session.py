"""
会话管理模型
"""
from sqlalchemy import Column, String, Text, ForeignKey, DateTime
from datetime import datetime
from .base import Base, TimestampMixin


class Session(Base):
    """会话表"""
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Session(id={self.id}, user_id={self.user_id})>"


class SessionInteraction(Base, TimestampMixin):
    """会话交互历史表"""
    __tablename__ = "session_interactions"

    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False)
    user_query = Column(Text, nullable=False)
    sql_query = Column(Text, nullable=True)
    query_plan = Column(Text, nullable=True)  # JSON - 查询计划
    chart_config = Column(Text, nullable=True)  # JSON
    summary = Column(Text, nullable=True)
    data_source_ids = Column(Text, nullable=True)  # JSON - 数据源ID列表
    temp_table_name = Column(String(100), nullable=True)  # 临时表名

    def __repr__(self):
        return f"<SessionInteraction(id={self.id}, session_id={self.session_id})>"


class ReportSnapshot(Base, TimestampMixin):
    """报表数据快照表（前10行）"""
    __tablename__ = "report_snapshots"

    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False)
    interaction_id = Column(String(36), ForeignKey("session_interactions.id"), nullable=False)
    data_snapshot = Column(Text, nullable=False)  # JSON

    def __repr__(self):
        return f"<ReportSnapshot(id={self.id}, interaction_id={self.interaction_id})>"
