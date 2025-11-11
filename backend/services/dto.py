"""
数据传输对象 (Data Transfer Objects)
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class DataMetadata(BaseModel):
    """数据元信息"""
    columns: List[str]
    column_types: Dict[str, str]
    row_count: int


class SQLQuery(BaseModel):
    """SQL查询"""
    db_config_id: str
    sql: str
    source_alias: str  # 用于临时表命名


class MCPCall(BaseModel):
    """MCP工具调用"""
    mcp_config_id: str
    tool_name: str
    parameters: Dict[str, Any]
    source_alias: str  # 用于临时表命名


class QueryPlan(BaseModel):
    """查询计划"""
    no_data_source_match: bool = False  # 是否无法匹配数据源
    user_message: Optional[str] = None  # 给用户的友好提示信息
    use_temp_table: bool = False  # 是否使用 session 临时表
    temp_table_name: Optional[str] = None  # 临时表名
    sql_queries: List[SQLQuery] = Field(default_factory=list)
    mcp_calls: List[MCPCall] = Field(default_factory=list)
    needs_combination: bool = False
    combination_strategy: Optional[str] = None


class ChartSuggestion(BaseModel):
    """图表建议"""
    chart_type: str
    chart_config: Optional[Dict[str, Any]] = None  # text 类型时可以为 None
    summary: str


class SensitiveRule(BaseModel):
    """敏感信息规则"""
    id: Optional[str] = None
    db_config_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    mode: str  # 'filter' or 'mask'
    columns: List[str]
    pattern: Optional[str] = None


class ConversationMessage(BaseModel):
    """会话消息"""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: Optional[datetime] = None
