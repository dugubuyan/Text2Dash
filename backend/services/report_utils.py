"""
报表服务工具函数
"""
import re
import json
from typing import Dict, List, Any, Optional
from .dto import QueryPlan


def build_sql_display(query_plan: QueryPlan) -> str:
    """
    构建用于显示的SQL查询字符串
    
    Args:
        query_plan: 查询计划
    
    Returns:
        SQL显示字符串
    """
    sql_parts = []
    
    # 添加SQL查询
    for i, sql_query in enumerate(query_plan.sql_queries, 1):
        sql_parts.append(f"-- 数据库查询 {i} ({sql_query.source_alias})")
        sql_parts.append(sql_query.sql)
        sql_parts.append("")
    
    # 添加MCP调用
    for i, mcp_call in enumerate(query_plan.mcp_calls, 1):
        sql_parts.append(f"-- MCP工具调用 {i} ({mcp_call.source_alias})")
        sql_parts.append(f"-- 工具: {mcp_call.tool_name}")
        sql_parts.append(f"-- 参数: {json.dumps(mcp_call.parameters, ensure_ascii=False)}")
        sql_parts.append("")
    
    return "\n".join(sql_parts)


def replace_placeholders_in_summary(
    summary: str,
    data: List[Dict[str, Any]]
) -> str:
    """
    替换 summary 中的数据占位符
    
    支持多种占位符格式：
    - {{DATA_PLACEHOLDER}}: 第一行第一列的值
    - {{DATA_PLACEHOLDER_X}}: 第一行第一列的值（通常是类别名）
    - {{DATA_PLACEHOLDER_1}}, {{DATA_PLACEHOLDER_2}}, ...: 第一行的第1、2、...列的值
    
    Args:
        summary: 包含占位符的摘要文本
        data: 数据列表
    
    Returns:
        替换后的摘要文本
    """
    from ..utils.logger import get_logger
    logger = get_logger(__name__)
    
    if not summary or "{{DATA_PLACEHOLDER" not in summary:
        return summary
    
    # 如果数据为空，替换所有占位符为"无数据"
    if not data or not data[0]:
        result = re.sub(r'\{\{DATA_PLACEHOLDER[^}]*\}\}', '无数据', summary)
        logger.debug(f"数据为空，替换所有占位符: '{summary}' -> '{result}'")
        return result
    
    # 获取第一行数据
    first_row = data[0]
    columns = list(first_row.keys())
    
    # 格式化值的辅助函数
    def format_value(value):
        if value is None:
            return "无数据"
        if isinstance(value, (int, float)):
            return f"{value:,}"
        return str(value)
    
    result = summary
    
    # 查找所有占位符
    placeholders = re.findall(r'\{\{DATA_PLACEHOLDER[^}]*\}\}', summary)
    
    for placeholder in placeholders:
        # 提取占位符类型
        if placeholder == "{{DATA_PLACEHOLDER}}":
            # 默认占位符：取第一列的值
            value = first_row.get(columns[0]) if columns else None
            formatted_value = format_value(value)
            result = result.replace(placeholder, formatted_value)
            logger.debug(f"替换 {placeholder} -> {formatted_value} (列: {columns[0] if columns else 'N/A'})")
            
        elif placeholder == "{{DATA_PLACEHOLDER_X}}":
            # X轴占位符：取第一列的值（通常是类别名）
            value = first_row.get(columns[0]) if columns else None
            formatted_value = format_value(value)
            result = result.replace(placeholder, formatted_value)
            logger.debug(f"替换 {placeholder} -> {formatted_value} (列: {columns[0] if columns else 'N/A'})")
            
        else:
            # 带索引的占位符：{{DATA_PLACEHOLDER_1}}, {{DATA_PLACEHOLDER_2}}, ...
            match = re.match(r'\{\{DATA_PLACEHOLDER_(\d+)\}\}', placeholder)
            if match:
                index = int(match.group(1)) - 1  # 转换为0-based索引
                if 0 <= index < len(columns):
                    column_name = columns[index]
                    value = first_row.get(column_name)
                    formatted_value = format_value(value)
                    result = result.replace(placeholder, formatted_value)
                    logger.debug(f"替换 {placeholder} -> {formatted_value} (列: {column_name})")
                else:
                    # 索引超出范围
                    result = result.replace(placeholder, "无数据")
                    logger.warning(f"占位符索引超出范围: {placeholder}, 列数: {len(columns)}")
    
    logger.debug(f"占位符替换完成: '{summary}' -> '{result}'")
    
    return result


def should_create_temp_table(query_plan: QueryPlan) -> bool:
    """
    判断是否需要创建临时表
    
    规则：
    1. 查询了原始数据源（非临时表）→ 需要创建
    2. 有 MCP 调用 → 需要创建
    3. 需要数据组合 → 需要创建
    4. 只查询临时表的简单子集 → 不需要创建
    
    Args:
        query_plan: 查询计划
        
    Returns:
        是否需要创建临时表
    """
    from ..utils.logger import get_logger
    logger = get_logger(__name__)
    
    # 规则1：查询了原始数据源
    if any(q.db_config_id != "__session__" for q in query_plan.sql_queries):
        logger.debug("需要创建临时表：查询了原始数据源")
        return True
    
    # 规则2：有 MCP 调用
    if len(query_plan.mcp_calls) > 0:
        logger.debug("需要创建临时表：有 MCP 调用")
        return True
    
    # 规则3：需要数据组合
    if query_plan.needs_combination:
        logger.debug("需要创建临时表：需要数据组合")
        return True
    
    # 规则4：只查询临时表的简单子集，不需要创建
    logger.debug("不需要创建临时表：简单临时表查询")
    return False
