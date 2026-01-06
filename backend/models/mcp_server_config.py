"""
MCP Server配置模型
"""
from sqlalchemy import Column, String, Text, Integer
from .base import Base, TimestampMixin


class MCPServerConfig(Base, TimestampMixin):
    """MCP Server配置表"""
    __tablename__ = "mcp_server_configs"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(Integer, nullable=False, default=0, index=True)
    name = Column(String(255), nullable=False)
    url = Column(Text, nullable=False)
    auth_type = Column(String(50), nullable=True)  # none, bearer, api_key
    encrypted_auth_token = Column(Text, nullable=True)
    available_tools = Column(Text, nullable=True)  # JSON array

    def __repr__(self):
        return f"<MCPServerConfig(id={self.id}, name={self.name}, url={self.url})>"
