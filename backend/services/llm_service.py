"""
LLM服务 - 使用LiteLLM集成大语言模型
"""
import os
import json
import asyncio
from typing import List, Dict, Any, Optional
from litellm import acompletion, completion_cost
import litellm

from backend.utils.logger import get_logger
from .dto import (
    QueryPlan,
    SQLQuery,
    MCPCall,
    ChartSuggestion,
    DataMetadata,
    SensitiveRule,
    ConversationMessage,
)
from .cache_service import get_cache_service

logger = get_logger(__name__)


class LLMService:
    """LLM服务类 - 处理所有与大语言模型的交互"""
    
    def __init__(self, default_model: str = None):
        """
        初始化LLM服务
        
        Args:
            default_model: 默认使用的模型名称
        """
        self.default_model = default_model or os.getenv(
            "DEFAULT_MODEL", 
            "gemini/gemini-2.0-flash"
        )
        
        # 配置LiteLLM
        litellm.set_verbose = os.getenv("LITELLM_VERBOSE", "False").lower() == "true"
        
        # 重试配置
        self.max_retries = 3
        self.retry_delay = 1  # 秒
        
        logger.info(f"LLM服务初始化完成，默认模型: {self.default_model}")
    
    async def _call_llm_with_retry(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        调用LLM并实现重试逻辑
        
        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
            response_format: 响应格式（如 {"type": "json_object"}）
        
        Returns:
            LLM响应内容
        
        Raises:
            Exception: 重试失败后抛出异常
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"调用LLM (尝试 {attempt + 1}/{self.max_retries}): model={model}")
                
                kwargs = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                
                if response_format:
                    kwargs["response_format"] = response_format
                
                # 记录发送给LLM的完整请求
                if messages:
                    logger.info(
                        f"LLM请求详情:\n"
                        f"  模型: {model}\n"
                        f"  温度: {temperature}\n"
                        f"  最大tokens: {max_tokens}\n"
                        f"  响应格式: {response_format}\n"
                        f"  消息数: {len(messages)}"
                    )
                    
                    # 打印所有消息内容
                    for i, msg in enumerate(messages):
                        role = msg.get('role', 'unknown')
                        content = msg.get('content', '')
                        logger.info(
                            f"  消息 {i+1} [{role}]:\n"
                            f"{'='*60}\n"
                            f"{content}\n"
                            f"{'='*60}"
                        )
                
                response = await acompletion(**kwargs)
                
                content = response.choices[0].message.content
                
                # 记录LLM响应
                logger.info(
                    f"LLM响应:\n"
                    f"{'='*60}\n"
                    f"{content}\n"
                    f"{'='*60}"
                )
                
                # 记录token使用情况
                if hasattr(response, 'usage'):
                    logger.info(
                        f"Token使用: prompt={response.usage.prompt_tokens}, "
                        f"completion={response.usage.completion_tokens}, "
                        f"total={response.usage.total_tokens}"
                    )
                
                return content
                
            except Exception as e:
                last_error = e
                logger.warning(
                    f"LLM调用失败 (尝试 {attempt + 1}/{self.max_retries}): {str(e)}",
                    exc_info=attempt == self.max_retries - 1
                )
                
                if attempt < self.max_retries - 1:
                    # 指数退避
                    delay = self.retry_delay * (2 ** attempt)
                    logger.debug(f"等待 {delay} 秒后重试...")
                    await asyncio.sleep(delay)
        
        # 所有重试都失败
        logger.error(f"LLM调用失败，已达到最大重试次数: {str(last_error)}")
        raise Exception(f"LLM服务调用失败: {str(last_error)}")

    async def generate_query_plan(
        self,
        query: str,
        db_schemas: Dict[str, Any],
        mcp_tools: Dict[str, Any],
        model: str = None,
        session_temp_tables: Optional[List[Dict[str, Any]]] = None,
    ) -> QueryPlan:
        """
        根据自然语言、数据库schema和MCP工具描述生成查询计划
        
        注意：query 应该是智能路由提供的 refined_query（精炼后的查询意图），
        而不是用户的原始输入。这样可以确保查询计划生成更准确。
        
        Args:
            query: 精炼后的查询意图（来自智能路由）
            db_schemas: 数据库schema信息 {db_id: schema_info}
            mcp_tools: MCP工具信息 {mcp_id: tools_info}
            model: 使用的模型（可选）
            session_temp_tables: session临时表信息（可选）
        
        Returns:
            QueryPlan对象，包含SQL查询和MCP工具调用
        """
        model = model or self.default_model
        
        # 尝试从缓存获取
        cache = get_cache_service()
        cache_key = cache._generate_key(
            "query_plan",
            {
                "query": query,
                "db_schemas": db_schemas,
                "mcp_tools": mcp_tools,
                "model": model
            }
        )
        
        cached_result = cache.get(cache_key)
        if cached_result:
            logger.info(f"查询计划缓存命中: query='{query[:50]}...'")
            # 从缓存的字典重建QueryPlan对象
            return QueryPlan(
                no_data_source_match=cached_result.get("no_data_source_match", False),
                user_message=cached_result.get("user_message"),
                sql_queries=[SQLQuery(**q) for q in cached_result.get("sql_queries", [])],
                mcp_calls=[MCPCall(**c) for c in cached_result.get("mcp_calls", [])],
                needs_combination=cached_result.get("needs_combination", False),
                combination_strategy=cached_result.get("combination_strategy")
            )
        
        logger.info(f"生成查询计划: query='{query[:50]}...', model={model}, temp_tables={len(session_temp_tables) if session_temp_tables else 0}")
        
        # 检查是否有可用数据源，如果没有则直接返回
        if not db_schemas and not mcp_tools and not session_temp_tables:
            logger.warning("没有可用的数据源，直接返回提示信息")
            return QueryPlan(
                no_data_source_match=True,
                user_message="当前没有配置任何数据源，请先在设置中添加数据库或MCP服务器",
                sql_queries=[],
                mcp_calls=[],
                needs_combination=False,
                combination_strategy=None
            )
        
        # 构建系统提示
        system_prompt = self._build_query_plan_system_prompt(db_schemas, mcp_tools, session_temp_tables)
        
        # 构建消息列表
        # 注意：不再添加对话历史，因为 query 已经是智能路由精炼后的完整意图
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请为以下查询生成执行计划：\n\n{query}"}
        ]
        
        try:
            # 调用LLM，要求返回JSON格式
            response = await self._call_llm_with_retry(
                messages=messages,
                model=model,
                temperature=0.3,  # 较低温度以获得更确定的结果
                response_format={"type": "json_object"}
            )
            
            # 解析响应
            plan_data = json.loads(response)
            
            # 构建QueryPlan对象
            query_plan = QueryPlan(
                no_data_source_match=plan_data.get("no_data_source_match", False),
                user_message=plan_data.get("user_message"),
                sql_queries=[SQLQuery(**q) for q in plan_data.get("sql_queries", [])],
                mcp_calls=[MCPCall(**c) for c in plan_data.get("mcp_calls", [])],
                needs_combination=plan_data.get("needs_combination", False),
                combination_strategy=plan_data.get("combination_strategy")
            )
            
            logger.info(
                f"查询计划生成成功: no_match={query_plan.no_data_source_match}, "
                f"{len(query_plan.sql_queries)} SQL查询, "
                f"{len(query_plan.mcp_calls)} MCP调用, "
                f"需要组合: {query_plan.needs_combination}"
            )
            
            # 保存到缓存
            cache.set(
                cache_key,
                {
                    "no_data_source_match": query_plan.no_data_source_match,
                    "user_message": query_plan.user_message,
                    "sql_queries": [
                        {
                            "db_config_id": q.db_config_id,
                            "sql": q.sql,
                            "source_alias": q.source_alias
                        }
                        for q in query_plan.sql_queries
                    ],
                    "mcp_calls": [
                        {
                            "mcp_config_id": c.mcp_config_id,
                            "tool_name": c.tool_name,
                            "parameters": c.parameters,
                            "source_alias": c.source_alias
                        }
                        for c in query_plan.mcp_calls
                    ],
                    "needs_combination": query_plan.needs_combination,
                    "combination_strategy": query_plan.combination_strategy
                },
                ttl=3600  # 缓存1小时
            )
            logger.debug(f"查询计划已缓存: key={cache_key}")
            
            return query_plan
            
        except json.JSONDecodeError as e:
            logger.error(f"解析LLM响应失败: {e}", exc_info=True)
            raise Exception(f"无法解析查询计划: {str(e)}")
        except Exception as e:
            logger.error(f"生成查询计划失败: {e}", exc_info=True)
            raise
    
    def _build_query_plan_system_prompt(
        self,
        db_schemas: Dict[str, Any],
        mcp_tools: Dict[str, Any],
        session_temp_tables: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """构建查询计划生成的系统提示"""
        prompt = """你是数据查询规划专家，你的职责是根据用户查询生成数据查询计划（SQL/MCP调用），不负责可视化。

可用数据源：

"""
        
        # 添加 session 临时表信息（如果有）
        if session_temp_tables:
            prompt += "## Session 临时表（历史查询结果，SQLite格式）\n\n"
            for temp_table in session_temp_tables:
                prompt += f"### 表名: {temp_table['table_name']}\n"
                prompt += f"来源查询: {temp_table.get('user_query', 'Unknown')}\n"
                prompt += f"行数: {temp_table.get('row_count', 0)}\n"
                prompt += "列:\n"
                for col in temp_table.get('columns', []):
                    prompt += f"  - {col['name']} ({col['type']})\n"
                prompt += "\n"
        
        # 添加数据库信息
        if db_schemas:
            prompt += "## 数据库\n\n"
            for db_id, schema in db_schemas.items():
                db_type = schema.get('type', 'Unknown')
                prompt += f"### 数据库ID: {db_id}\n"
                prompt += f"名称: {schema.get('name', 'Unknown')}\n"
                prompt += f"**类型: {db_type.upper()}**\n"
                
                # 如果有schema描述文件，使用描述文件内容
                if 'schema_description' in schema:
                    prompt += "数据库结构描述:\n"
                    prompt += schema['schema_description']
                    prompt += "\n\n"
                else:
                    # 否则使用表结构信息
                    prompt += "表结构:\n"
                    tables = schema.get('tables', {})
                    for table_name, columns in tables.items():
                        column_names = [col['name'] for col in columns]
                        prompt += f"  - {table_name}: {', '.join(column_names)}\n"
                    prompt += "\n"
        
        # 添加MCP工具信息
        has_mcp_tools = bool(mcp_tools)
        if has_mcp_tools:
            prompt += "## MCP工具\n\n"
            for mcp_id, tools in mcp_tools.items():
                prompt += f"### MCP Server ID: {mcp_id}\n"
                prompt += f"名称: {tools.get('name', 'Unknown')}\n"
                prompt += "可用工具:\n"
                for tool in tools.get('tools', []):
                    prompt += f"  - {tool['name']}: {tool.get('description', '')}\n"
                    if tool.get('parameters'):
                        prompt += f"    参数: {json.dumps(tool['parameters'], ensure_ascii=False)}\n"
                prompt += "\n"
        else:
            prompt += "## MCP工具\n\n**当前没有配置MCP工具**\n\n"
        
        # 根据是否有MCP工具，调整返回格式说明
        if has_mcp_tools:
            mcp_calls_example = """  "mcp_calls": [
    {
      "mcp_config_id": "MCP Server ID",
      "tool_name": "工具名称",
      "parameters": {"参数名": "参数值"},
      "source_alias": "结果别名"
    }
  ],"""
        else:
            mcp_calls_example = """  "mcp_calls": [],"""
        
        prompt += f"""
返回JSON格式：

{{
  "no_data_source_match": false,
  "user_message": null,
  "sql_queries": [
    {{
      "db_config_id": "数据库ID或'__session__'（临时表）",
      "sql": "SQL查询语句",
      "source_alias": "结果别名"
    }}
  ],
{mcp_calls_example}
  "needs_combination": true/false
}}

核心能力：

1. **数据源**：
   - 临时表：db_config_id="__session__"
   - 数据库：使用对应的 db_config_id
   - MCP工具：使用对应的 mcp_config_id（如上面有列出）
   - 查询与所有数据源无关：设置 no_data_source_match=true

2. **SQL要求**：
   - 只生成 SELECT 查询
   - 根据数据库类型使用对应的SQL方言
   - 聚合函数必须指定别名（如 COUNT(*) AS total_count）

3. **多查询组合**：
   - 可以生成多个 sql_queries 和 mcp_calls，每个结果会存入临时表 temp_{{source_alias}}
   - 如需组合多个结果，设置 needs_combination=true
   - 系统会自动调用第二次LLM来生成组合SQL
   - 优先使用子查询或 CTE 在单个 SQL 中完成，避免多查询组合
"""
        
        return prompt

    async def generate_combination_sql(
        self,
        query: str,
        temp_table_info: Dict[str, Any],
        model: str = None,
    ) -> str:
        """
        生成用于组合临时表数据的SQL语句
        
        Args:
            query: 用户的原始查询
            temp_table_info: 临时表信息 {table_name: {columns, types, source}}
            model: 使用的模型（可选）
        
        Returns:
            SQL组合语句
        """
        model = model or self.default_model
        
        logger.info(f"生成数据组合SQL: query='{query[:50]}...', tables={list(temp_table_info.keys())}")
        
        # 构建系统提示
        system_prompt = self._build_combination_sql_system_prompt(temp_table_info)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"请生成SQL语句来组合这些临时表的数据，以满足以下查询需求：\n\n{query}"
            }
        ]
        
        try:
            response = await self._call_llm_with_retry(
                messages=messages,
                model=model,
                temperature=0.2,  # 低温度以获得准确的SQL
                response_format={"type": "json_object"}
            )
            
            # 解析响应
            result = json.loads(response)
            sql = result.get("sql", "")
            
            if not sql:
                raise Exception("LLM未返回SQL语句")
            
            logger.info(f"组合SQL生成成功: {sql[:100]}...")
            
            return sql
            
        except json.JSONDecodeError as e:
            logger.error(f"解析LLM响应失败: {e}", exc_info=True)
            raise Exception(f"无法解析组合SQL: {str(e)}")
        except Exception as e:
            logger.error(f"生成组合SQL失败: {e}", exc_info=True)
            raise
    
    def _build_combination_sql_system_prompt(
        self,
        temp_table_info: Dict[str, Any]
    ) -> str:
        """构建组合SQL生成的系统提示"""
        prompt = """你是SQL专家，需要生成SQL来组合多个临时表的数据。

可用临时表：

"""
        
        for table_name, info in temp_table_info.items():
            prompt += f"## {table_name}\n"
            prompt += f"来源: {info.get('source', 'Unknown')}\n"
            prompt += "列:\n"
            for col_name, col_type in info.get('columns', {}).items():
                prompt += f"  - {col_name} ({col_type})\n"
            prompt += f"行数: {info.get('row_count', 0)}\n\n"
        
        prompt += """
返回JSON格式：

{
  "sql": "SELECT ... FROM ... JOIN/UNION ...",
  "explanation": "组合策略说明"
}

规则：
1. 使用SQLite兼容语法
2. 列名冲突时使用别名
3. 只生成SELECT查询
4. 计算字段和聚合函数必须使用 AS 指定别名（如 COUNT(*) AS total_count）
"""
        
        return prompt

    async def analyze_data_and_suggest_chart(
        self,
        query: str,
        metadata: DataMetadata,
        model: str = None,
        sql_query: str = None,
        use_cache: bool = True,
    ) -> ChartSuggestion:
        """
        分析数据元信息，推荐图表类型并生成总结
        
        注意：只接收元信息，不接收原始数据
        
        Args:
            query: 用户的原始查询
            metadata: 数据元信息（列名、类型、行数）
            model: 使用的模型（可选）
            sql_query: SQL查询语句（可选，用于日志记录）
            use_cache: 是否使用缓存（可选，默认True）
                - True: 使用缓存，相同数据结构返回相同图表（适用于新查询场景）
                - False: 跳过缓存，强制调用LLM生成新图表（适用于reuse_data场景）
        
        Returns:
            ChartSuggestion对象，包含图表类型、配置和总结
        """
        model = model or self.default_model
        
        # 尝试从缓存获取（如果启用缓存）
        cache = get_cache_service()
        cache_key = None
        
        if use_cache:
            # 对列名和类型排序，确保顺序不影响缓存
            sorted_columns = tuple(sorted(metadata.columns))
            sorted_column_types = tuple(sorted(metadata.column_types.items()))
            
            cache_data = {
                "columns": sorted_columns,
                "column_types": sorted_column_types,
                "row_count": metadata.row_count,
                "model": model,
                "query": query  # 包含query确保不同意图生成不同图表
            }
            
            cache_key = cache._generate_key("chart_suggestion", cache_data)
            
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info(
                    f"图表分析缓存命中: "
                    f"columns={metadata.columns}, rows={metadata.row_count}"
                )
                return ChartSuggestion(
                    chart_type=cached_result["chart_type"],
                    chart_config=cached_result["chart_config"],
                    summary=cached_result["summary"]
                )
        else:
            logger.info(f"图表分析跳过缓存（use_cache=False）")
        
        # 检查数据是否为空
        if metadata.row_count == 0:
            logger.info(f"查询结果为空，返回空数据提示")
            empty_result = ChartSuggestion(
                chart_type="empty",
                chart_config={
                    "type": "empty",
                    "message": "查询未返回任何数据"
                },
                summary="查询执行成功，但未找到符合条件的数据。请尝试调整查询条件或检查数据源。"
            )
            
            # 缓存空数据结果（如果启用缓存）
            if use_cache and cache_key:
                cache.set(
                    cache_key,
                    {
                        "chart_type": empty_result.chart_type,
                        "chart_config": empty_result.chart_config,
                        "summary": empty_result.summary
                    },
                    ttl=3600
                )
            
            return empty_result
        
        logger.info(
            f"分析数据并推荐图表: query='{query[:50]}...', "
            f"columns={len(metadata.columns)}, rows={metadata.row_count}"
        )
        
        # 构建系统提示
        system_prompt = self._build_chart_suggestion_system_prompt()
        
        # 构建数据元信息描述
        metadata_desc = f"""
数据元信息：
- 列数: {len(metadata.columns)}
- 行数: {metadata.row_count}
- 列信息:
"""
        for col in metadata.columns:
            col_type = metadata.column_types.get(col, "unknown")
            metadata_desc += f"  - {col} ({col_type})\n"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"""用户查询: {query}

{metadata_desc}

请根据以上信息推荐合适的图表类型，生成Echarts配置，并提供数据分析总结。"""
            }
        ]
        
        try:
            response = await self._call_llm_with_retry(
                messages=messages,
                model=model,
                temperature=0.5,
                response_format={"type": "json_object"}
            )
            
            # 记录LLM原始响应，便于调试
            logger.debug(f"LLM原始响应: {response}")
            
            # 解析响应
            result = json.loads(response)
            
            # 处理 chart_config：text 类型时可以为 None
            chart_type = result.get("chart_type", "bar")
            chart_config = result.get("chart_config")
            if chart_config is None and chart_type != "text":
                chart_config = {}  # 非 text 类型时提供默认空字典
            
            chart_suggestion = ChartSuggestion(
                chart_type=chart_type,
                chart_config=chart_config,
                summary=result.get("summary", "")
            )
            
            logger.info(f"图表推荐成功: type={chart_suggestion.chart_type}")
            
            # 保存到缓存（如果启用缓存）
            if use_cache and cache_key:
                cache.set(
                    cache_key,
                    {
                        "chart_type": chart_suggestion.chart_type,
                        "chart_config": chart_suggestion.chart_config,
                        "summary": chart_suggestion.summary
                    },
                    ttl=3600  # 缓存1小时
                )
                logger.debug(f"图表分析已缓存: key={cache_key}")
            
            return chart_suggestion
            
        except json.JSONDecodeError as e:
            logger.error(f"解析LLM响应失败: {e}")
            logger.error(f"LLM返回的原始响应内容: {response}")
            raise Exception(f"无法解析图表建议: {str(e)}")
        except Exception as e:
            logger.error(f"生成图表建议失败: {e}", exc_info=True)
            raise
    
    def _build_chart_suggestion_system_prompt(self) -> str:
        """构建图表建议生成的系统提示"""
        return """你是数据可视化专家，根据用户查询和数据特征推荐合适的展示方式。

## 展示方式选择

### 1. 文本展示（text）
适用场景：
- 单个数值（总数、平均值、最大值等），或者是单列数据
- 简单的统计结果
- 少量文字描述

返回格式：
{
  "chart_type": "text",
  "chart_config": null,
  "summary": "直接展示答案，如：总销售额为 1,234,567 元"
}

### 2. 图表展示
适用场景：
- 多条数据记录
- 需要对比分析
- 趋势展示
- 分布情况

支持的图表类型：bar（柱状图）、line（折线图）、pie（饼图）、scatter（散点图）、radar（雷达图）、heatmap（热力图）

返回格式：

#### 柱状图/折线图：
{
  "chart_type": "bar/line",
  "chart_config": {
    "title": {"text": "图表标题"},
    "tooltip": {"trigger": "axis"},
    "xAxis": {"type": "category", "data": "{{DATA_PLACEHOLDER_X}}"},
    "yAxis": {"type": "value", "name": "Y轴名称"},
    "series": [{
      "name": "系列名称",
      "type": "bar/line",
      "data": "{{DATA_PLACEHOLDER}}"
    }]
  },
  "summary": "数据分析总结"
}

#### 散点图：
{
  "chart_type": "scatter",
  "chart_config": {
    "title": {"text": "图表标题"},
    "tooltip": {"trigger": "item"},
    "xAxis": {"type": "value", "name": "X轴名称（第1列）"},
    "yAxis": {"type": "value", "name": "Y轴名称（第2列）"},
    "series": [{
      "name": "系列名称",
      "type": "scatter",
      "data": "{{DATA_PLACEHOLDER}}"
    }]
  },
  "summary": "数据分析总结"
}

注意：散点图的xAxis和yAxis都必须是type: "value"，不需要指定data

#### 雷达图：
{
  "chart_type": "radar",
  "chart_config": {
    "title": {"text": "图表标题"},
    "tooltip": {"trigger": "item"},
    "radar": {
      "indicator": "{{DATA_PLACEHOLDER}}"
    },
    "series": [{
      "name": "系列名称",
      "type": "radar",
      "data": "{{DATA_PLACEHOLDER}}"
    }]
  },
  "summary": "数据分析总结"
}

注意：雷达图用于展示多维度数据，每行数据包含多个数值维度。indicator会自动根据数据列生成

### 3. 多图表展示
当数据包含多个维度或用户明确要求多个指标时，可以返回多个图表：

{
  "chart_type": "multiple",
  "chart_config": {
    "charts": [
      {
        "title": "图表1标题",
        "type": "bar",
        "config": {...}
      },
      {
        "title": "图表2标题",
        "type": "line",
        "config": {...}
      }
    ]
  },
  "summary": "综合分析总结"
}

## 配置规则

1. 数据占位符：series.data 用 "{{DATA_PLACEHOLDER}}"，xAxis.data 用 "{{DATA_PLACEHOLDER_X}}"
2. 不需要的字段直接省略
3. 不使用 formatter 等函数
4. 配置必须是有效的JSON

## 示例

用户查询："今天的总销售额是多少"
数据：1行1列（单个数值）
返回：
{
  "chart_type": "text",
  "chart_config": null,
  "summary": "今天的总销售额为 {{DATA_PLACEHOLDER}} 元"
}

用户查询："各部门的销售额"
数据：多行2列（部门、销售额）
返回：
{
  "chart_type": "bar",
  "chart_config": {
    "title": {"text": "各部门销售额"},
    "tooltip": {"trigger": "axis"},
    "xAxis": {"type": "category", "data": "{{DATA_PLACEHOLDER_X}}"},
    "yAxis": {"type": "value"},
    "series": [{
      "name": "销售额",
      "type": "bar",
      "data": "{{DATA_PLACEHOLDER}}"
    }]
  },
  "summary": "展示各部门销售额对比"
}

用户查询："显示销售额和利润的对比"
数据：多行3列（部门、销售额、利润）
返回：
{
  "chart_type": "multiple",
  "chart_config": {
    "charts": [
      {
        "title": "销售额对比",
        "type": "bar",
        "config": {...}
      },
      {
        "title": "利润对比",
        "type": "bar",
        "config": {...}
      }
    ]
  },
  "summary": "展示各部门销售额和利润的对比情况"
}

用户查询："各专业平均薪资与GPA的关系"
数据：多行2列（average_gpa, average_salary）
返回：
{
  "chart_type": "scatter",
  "chart_config": {
    "title": {"text": "各专业平均薪资与GPA的关系"},
    "tooltip": {"trigger": "item"},
    "xAxis": {"type": "value", "name": "平均GPA"},
    "yAxis": {"type": "value", "name": "平均薪资"},
    "series": [{
      "name": "专业",
      "type": "scatter",
      "data": "{{DATA_PLACEHOLDER}}"
    }]
  },
  "summary": "散点图展示各专业平均薪资与GPA的关系，可以观察GPA与薪资是否存在相关性。"
}

用户查询："各专业的GPA和薪资对比"
数据：多行3列（major_name, avg_gpa, avg_salary）
返回：
{
  "chart_type": "radar",
  "chart_config": {
    "title": {"text": "各专业GPA与薪资雷达图"},
    "tooltip": {"trigger": "item"},
    "radar": {
      "indicator": "{{DATA_PLACEHOLDER}}"
    },
    "series": [{
      "name": "专业数据",
      "type": "radar",
      "data": "{{DATA_PLACEHOLDER}}"
    }]
  },
  "summary": "雷达图展示各专业在GPA和薪资两个维度上的表现，便于多维度对比。"
}
"""

    async def summarize_conversation(
        self,
        conversation_history: List[ConversationMessage],
        model: str = None,
    ) -> str:
        """
        压缩会话历史，防止上下文爆炸
        
        Args:
            conversation_history: 会话历史消息列表
            model: 使用的模型（可选）
        
        Returns:
            压缩后的会话摘要
        """
        model = model or self.default_model
        
        logger.info(f"压缩会话历史: {len(conversation_history)} 条消息")
        
        # 构建对话历史文本
        conversation_text = ""
        for msg in conversation_history:
            role_name = "用户" if msg.role == "user" else "助手"
            conversation_text += f"{role_name}: {msg.content}\n\n"
        
        system_prompt = """你是会话摘要专家，将对话历史压缩成简洁摘要。

返回JSON格式：
{
  "summary": "会话摘要文本",
  "key_points": ["关键点1", "关键点2", "..."]
}

要求：
1. 保留关键信息：用户需求、查询数据、报表类型
2. 保留重要上下文：数据源、时间范围、筛选条件
3. 去除冗余信息
4. 简洁表达
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"请压缩以下对话历史：\n\n{conversation_text}"
            }
        ]
        
        try:
            response = await self._call_llm_with_retry(
                messages=messages,
                model=model,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response)
            summary = result.get("summary", "")
            
            logger.info(f"会话压缩成功: {len(summary)} 字符")
            
            return summary
            
        except json.JSONDecodeError as e:
            logger.error(f"解析LLM响应失败: {e}", exc_info=True)
            # 如果解析失败，返回简单的摘要
            return f"会话包含 {len(conversation_history)} 条消息"
        except Exception as e:
            logger.error(f"压缩会话失败: {e}", exc_info=True)
            # 如果压缩失败，返回简单的摘要
            return f"会话包含 {len(conversation_history)} 条消息"

    async def parse_sensitive_rule(
        self,
        natural_language: str,
        available_columns: List[str] = None,
        db_schema_info: Dict[str, Any] = None,
        model: str = None,
    ) -> SensitiveRule:
        """
        将自然语言转换为结构化的敏感信息规则
        
        Args:
            natural_language: 自然语言描述的规则
            available_columns: 可用的列名列表（可选，已废弃，使用db_schema_info代替）
            db_schema_info: 数据库schema信息（可选）
            model: 使用的模型（可选）
        
        Returns:
            SensitiveRule对象
        """
        model = model or self.default_model
        
        logger.info(f"解析敏感信息规则: '{natural_language[:50]}...', has_schema={db_schema_info is not None}")
        
        system_prompt = self._build_sensitive_rule_system_prompt(available_columns, db_schema_info)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"请将以下规则转换为结构化格式：\n\n{natural_language}"
            }
        ]
        
        try:
            response = await self._call_llm_with_retry(
                messages=messages,
                model=model,
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response)
            
            # Handle case where LLM returns a list instead of dict
            if isinstance(result, list):
                if len(result) > 0:
                    result = result[0]
                else:
                    raise Exception("LLM返回空列表")
            
            sensitive_rule = SensitiveRule(
                name=result.get("name", "未命名规则"),
                description=result.get("description", natural_language),
                mode=result.get("mode", "mask"),
                columns=result.get("columns", []),
                pattern=result.get("pattern")
            )
            
            logger.info(
                f"敏感规则解析成功: name={sensitive_rule.name}, "
                f"mode={sensitive_rule.mode}, columns={sensitive_rule.columns}"
            )
            
            return sensitive_rule
            
        except json.JSONDecodeError as e:
            logger.error(f"解析LLM响应失败: {e}", exc_info=True)
            raise Exception(f"无法解析敏感信息规则: {str(e)}")
        except Exception as e:
            logger.error(f"解析敏感规则失败: {e}", exc_info=True)
            raise
            raise
    
    def _build_sensitive_rule_system_prompt(
        self,
        available_columns: List[str] = None,
        db_schema_info: Dict[str, Any] = None
    ) -> str:
        """构建敏感规则解析的系统提示"""
        prompt = """你是数据安全专家，将自然语言转换为敏感信息过滤规则。

处理模式：
- filter: 完全移除列
- mask: 脱敏处理

"""
        
        # 优先使用db_schema_info
        if db_schema_info:
            prompt += "## 数据库结构信息\n\n"
            
            # 如果有schema描述文件，使用描述文件内容
            if 'schema_description' in db_schema_info:
                prompt += "数据库详细描述：\n"
                prompt += db_schema_info['schema_description']
                prompt += "\n\n"
            else:
                # 否则使用表结构信息
                tables = db_schema_info.get('tables', {})
                if tables:
                    prompt += "数据库表和字段：\n"
                    for table_name, columns in tables.items():
                        column_info = []
                        for col in columns:
                            col_name = col['name']
                            col_type = col.get('type', 'UNKNOWN')
                            column_info.append(f"{col_name} ({col_type})")
                        prompt += f"  - {table_name}: {', '.join(column_info)}\n"
                    prompt += "\n"
        elif available_columns:
            prompt += f"可用列名：{', '.join(available_columns)}\n\n"
        
        prompt += """返回JSON格式：

{
  "name": "规则名称",
  "description": "规则描述",
  "mode": "filter 或 mask",
  "columns": ["列名1", "列名2"],
  "pattern": "脱敏模式（mask模式时需要）"
}

## 脱敏模式

### 预定义模式：
- "phone": 手机号，保留前3位和后4位
- "email": 邮箱，保留首字符和域名
- "id_card": 身份证，保留前6位和后4位
- "keep_first_N": 保留前N位
- "keep_last_N": 保留后N位

### 自定义规则（JSON字符串）：

Custom类型：
{
  "type": "custom",
  "keep_start": 3,
  "keep_end": 4,
  "mask_char": "*"
}

Regex类型：
{
  "type": "regex",
  "pattern": "\\\\d",
  "replacement": "X"
}

Range类型：
{
  "type": "range",
  "ranges": [[3, 7]],
  "mask_char": "#"
}

## 示例

"隐藏身份证号和手机号" →
{
  "name": "隐藏个人身份信息",
  "description": "隐藏身份证号和手机号",
  "mode": "filter",
  "columns": ["身份证号", "手机号", "id_card", "phone"],
  "pattern": null
}

"手机号只显示前3位和后4位" →
{
  "name": "手机号脱敏",
  "description": "手机号只显示前3位和后4位",
  "mode": "mask",
  "columns": ["手机号", "phone", "mobile"],
  "pattern": "phone"
}

"银行卡号保留前4位和后4位" →
{
  "name": "银行卡号脱敏",
  "description": "银行卡号保留前4位和后4位",
  "mode": "mask",
  "columns": ["银行卡号", "card_number", "bank_card"],
  "pattern": "{\\"type\\": \\"custom\\", \\"keep_start\\": 4, \\"keep_end\\": 4, \\"mask_char\\": \\"*\\"}"
}

## 重要规则

1. **优先使用数据库schema信息**：
   - 如果提供了数据库结构信息，必须从实际存在的表和字段中选择
   - 返回的列名必须是数据库中真实存在的字段名（精确匹配）
   - 根据字段名称和类型推断是否包含敏感信息

2. **字段识别策略**：
   - 身份证号：id_card, id_card_number, identity_card, idcard等
   - 手机号：phone, mobile, phone_number, mobile_number, contact_number等
   - 邮箱：email, email_address, mail等
   - 姓名：name, full_name, student_name, faculty_name等
   - 地址：address, home_address, contact_address等
   - 银行卡：bank_card, card_number, account_number等

3. **通用规则**：
   - 识别多种可能的列名（中文、英文、缩写）
   - 常见场景使用预定义模式
   - 特殊需求使用自定义规则
   - filter模式的pattern为null
   - 自定义规则必须是有效JSON字符串

4. **无schema信息时**：
   - 如果没有提供数据库schema，返回通用的列名建议
   - 在columns中包含多种可能的列名变体
"""
        
        return prompt

    # ============ 智能路由相关方法 ============
    
    async def smart_route(
        self,
        query: str,
        all_interactions: List[Dict[str, Any]],
        data_source_summary: Dict[str, Any],
        model: str = None
    ):
        """
        智能路由：分析用户意图并决策执行路径
        
        Args:
            query: 用户当前查询
            all_interactions: 会话的所有交互历史（按时间升序）
            data_source_summary: 数据源概要信息
            model: 使用的模型
        
        Returns:
            ExecutionPlan 对象
        """
        from .dto import ExecutionPlan
        
        model = model or self.default_model
        
        logger.info(f"智能路由分析: query='{query[:50]}...', interactions={len(all_interactions)}, model={model}")
        
        # 构建系统提示
        system_prompt = self._build_smart_router_prompt(
            all_interactions,
            data_source_summary
        )
        
        # 构建消息列表 - 只包含系统提示和当前查询
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
        
        try:
            # 调用LLM
            response = await self._call_llm_with_retry(
                messages=messages,
                model=model,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            # 解析响应
            data = json.loads(response)
            
            # 构建ExecutionPlan对象
            plan = ExecutionPlan(
                action=data.get("action", "query_new_data_with_chart"),
                direct_response=data.get("direct_response"),
                needs_chart_generation=data.get("needs_chart_generation", False),
                reuse_previous_data=data.get("reuse_previous_data", False),
                query_temp_table=data.get("query_temp_table", False),
                suggestions=data.get("suggestions"),
                refined_query=data.get("refined_query")
            )
            
            logger.info(
                f"智能路由完成: action={plan.action}, "
                f"needs_chart={plan.needs_chart_generation}, "
                f"refined_query={plan.refined_query or 'N/A'}"
            )
            
            return plan
            
        except Exception as e:
            logger.error(f"智能路由失败: {e}", exc_info=True)
            # 失败时返回默认计划（完整查询）
            return ExecutionPlan(
                action="query_new_data_with_chart",
                needs_chart_generation=True
            )
    
    def _build_smart_router_prompt(
        self,
        all_interactions: List[Dict[str, Any]],
        data_source_summary: Dict[str, Any]
    ) -> str:
        """构建智能路由的系统提示"""
        
        # 数据源描述
        sources_desc = []
        for db in data_source_summary.get("databases", []):
            sources_desc.append(f"- {db['name']}：{db['description']}")
        
        for mcp in data_source_summary.get("mcp_servers", []):
            sources_desc.append(f"- {mcp['name']}：{mcp['description']}")
        
        sources_text = "\n".join(sources_desc) if sources_desc else "无"
        
        # 构建交互历史描述
        interactions_text = "无"
        last_was_guidance = False  # 标记最后一次交互是否是系统引导
        
        if all_interactions:
            interactions_list = []
            for i, interaction in enumerate(all_interactions, 1):
                query = interaction.get("user_query", "")
                summary = interaction.get("summary", "")
                temp_table = interaction.get("temp_table_name", "")
                row_count = interaction.get("row_count", 0)
                columns = interaction.get("columns", [])
                
                interaction_desc = f"{i}. 用户: {query}"
                if summary:
                    interaction_desc += f"\n   系统: {summary}"
                    # 检测是否是引导性回复
                    if "请问" in summary or "想查询" in summary or "哪些方面" in summary or "建议" in summary:
                        last_was_guidance = True
                    else:
                        last_was_guidance = False
                if temp_table:
                    interaction_desc += f"\n   数据: {temp_table} (行数={row_count}, 列={columns})"
                
                interactions_list.append(interaction_desc)
            
            interactions_text = "\n\n".join(interactions_list)
        
        # 如果最后一次是引导，添加特别提示
        guidance_hint = ""
        if last_was_guidance:
            guidance_hint = "\n\n⚠️ **重要提示**：最后一次交互是系统的引导性问题，当前用户输入很可能是对该引导的回应。请结合引导内容理解用户意图，避免重复引导。"
        
        return f"""你是智能路由助手，分析并结合会话历史总结用户意图，决定执行路径。

## 可用数据源
{sources_text}

## 会话历史
{interactions_text}{guidance_hint}

## 执行动作

1. **direct_conversation** - 闲聊、问候、与数据无关的对话
2. **clarify_and_guide** - 意图不明确，需要引导（如"查一下数据"）
3. **reuse_data_regenerate_chart** - 相同数据，改变展示（如"换成柱状图"、"显示前5名"）
4. **query_temp_table_with_chart** - 在已有数据上筛选（如"只看计算机系"）
5. **query_new_data_with_chart** - 查询全新数据
6. **query_data_only** - 只查数据，不生成图表

## 返回格式

```json
{{
  "action": "动作类型",
  "direct_response": "直接回复（可选）",
  "needs_chart_generation": true/false,
  "reuse_previous_data": true/false,
  "query_temp_table": true/false,
  "suggestions": ["建议1", "建议2"],
  "refined_query": "总结的查询意图"
}}
```

## refined_query 说明

如果不是闲聊或引导，需要生成 refined_query 来总结用户的查询意图。

要求：
- 结合上下文理解完整意图
- 补全省略的信息
- 保持自然语言表达

示例：
- 用户："平均薪资吧" + 上下文 → "各系的平均薪资"
- 用户："15岁的" + 系统问"想查询什么" → "查询15岁的学生信息"

## 决策要点

1. **识别引导-回应模式**：如果上一轮是系统引导，当前输入是补充信息，应该：
   - 结合引导内容以及上下文理解用户意图
   - 选择合适的执行动作（通常是 query_new_data_with_chart）
   - **避免再次引导**

2. **上下文连贯性**：
   - 如果不是第一次交互，用户的输入通常是对上文的补充
   - 需要结合历史交互理解完整意图，历史交互信息中请偏重AI回复内容
   - 如果仍然不明确，才使用 clarify_and_guide

3. **数据复用判断**：
   - 能直接回复就回复
   - 意图明确就查询"""
    
    async def generate_schema_summary(
        self,
        schema_description: str,
        db_name: str,
        model: str = None
    ) -> str:
        """
        从详细的 schema description 生成简洁的 schema summary
        
        Args:
            schema_description: 详细的 schema 描述
            db_name: 数据库名称
            model: 使用的模型
        
        Returns:
            简洁的 schema 概要（~500 tokens）
        """
        model = model or self.default_model
        
        prompt = f"""从以下数据库 schema 生成简洁的业务概要（300字以内）。

数据库：{db_name}
Schema：{schema_description[:10000]}

要求：
1. 业务范围（1-2句话）
2. 主要业务模块（列表）
3. 不包含的业务（可选）

格式：简洁的 Markdown，不要技术细节。

输出："""
        
        try:
            messages = [
                {"role": "system", "content": "你是数据库架构分析专家。"},
                {"role": "user", "content": prompt}
            ]
            
            response = await self._call_llm_with_retry(
                messages=messages,
                model=model,
                temperature=0.3
            )
            
            logger.info(f"Schema summary 生成成功: {db_name}")
            return response.strip()
            
        except Exception as e:
            logger.error(f"生成 schema summary 失败: {e}", exc_info=True)
            return f"# {db_name}\n\n数据库概要生成失败，请手动配置。"
    
    async def generate_schema_summary_from_tables(
        self,
        table_names: List[str],
        db_name: str,
        model: str = None
    ) -> str:
        """
        从表名列表生成 schema summary
        
        Args:
            table_names: 表名列表
            db_name: 数据库名称
            model: 使用的模型
        
        Returns:
            简洁的 schema 概要
        """
        model = model or self.default_model
        
        # 限制表名数量
        tables_text = ', '.join(table_names[:50])
        if len(table_names) > 50:
            tables_text += f"等（共{len(table_names)}个表）"
        
        prompt = f"""根据表名推断数据库业务范围（200字以内）。

数据库：{db_name}
表名：{tables_text}

输出简洁的业务概要。"""
        
        try:
            messages = [
                {"role": "system", "content": "你是数据库架构分析专家。"},
                {"role": "user", "content": prompt}
            ]
            
            response = await self._call_llm_with_retry(
                messages=messages,
                model=model,
                temperature=0.3
            )
            
            logger.info(f"Schema summary 从表名生成成功: {db_name}")
            return response.strip()
            
        except Exception as e:
            logger.error(f"从表名生成 schema summary 失败: {e}", exc_info=True)
            # 返回简单的表名列表
            if len(table_names) <= 20:
                return f"# {db_name}\n\n包含表：{', '.join(table_names)}"
            else:
                return f"# {db_name}\n\n包含{len(table_names)}个表，主要有：{', '.join(table_names[:20])}等"
