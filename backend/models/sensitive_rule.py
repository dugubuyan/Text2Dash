"""
敏感信息规则模型
"""
from sqlalchemy import Column, String, Text, ForeignKey
from .base import Base, TimestampMixin


class SensitiveRule(Base, TimestampMixin):
    """敏感信息规则表"""
    __tablename__ = "sensitive_rules"

    id = Column(String(36), primary_key=True)
    db_config_id = Column(String(36), ForeignKey("database_configs.id"), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    mode = Column(String(20), nullable=False)  # filter or mask
    columns = Column(Text, nullable=False)  # JSON array
    pattern = Column(Text, nullable=True)

    def __repr__(self):
        return f"<SensitiveRule(id={self.id}, name={self.name}, mode={self.mode})>"
