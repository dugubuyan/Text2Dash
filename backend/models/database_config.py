"""
数据库配置模型
"""
from sqlalchemy import Column, String, Text, Boolean, Integer
from .base import Base, TimestampMixin


class DatabaseConfig(Base, TimestampMixin):
    """数据库配置表"""
    __tablename__ = "database_configs"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(Integer, nullable=False, default=0, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # sqlite, mysql, postgresql
    url = Column(Text, nullable=False)
    username = Column(String(255), nullable=True)
    encrypted_password = Column(Text, nullable=True)
    use_schema_file = Column(Boolean, default=False, nullable=False)  # 是否使用schema描述文件
    schema_description = Column(Text, nullable=True)  # schema描述文件内容（详细版，用于查询生成）
    schema_summary = Column(Text, nullable=True)  # schema概要（简洁版，用于智能路由）

    def __repr__(self):
        return f"<DatabaseConfig(id={self.id}, name={self.name}, type={self.type})>"
