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
        context: List[ConversationMessage],
        model: str = None,
        session_temp_tables: Optional[List[Dict[str, Any]]] = None,
    ) -> QueryPlan:
        """
        根据自然语言、数据库schema和MCP工具描述生成查询计划
        
        Args:
            query: 用户的自然语言查询
            db_schemas: 数据库schema信息 {db_id: schema_info}
            mcp_tools: MCP工具信息 {mcp_id: tools_info}
            context: 会话上下文
            model: 使用的模型（可选）
        
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
                use_temp_table=cached_result.get("use_temp_table", False),
                temp_table_name=cached_result.get("temp_table_name"),
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
        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加上下文
        for msg in context[-5:]:  # 只取最近5条消息
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # 添加当前查询
        messages.append({
            "role": "user",
            "content": f"请为以下查询生成执行计划：\n\n{query}"
        })
        
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
                use_temp_table=plan_data.get("use_temp_table", False),
                temp_table_name=plan_data.get("temp_table_name"),
                sql_queries=[SQLQuery(**q) for q in plan_data.get("sql_queries", [])],
                mcp_calls=[MCPCall(**c) for c in plan_data.get("mcp_calls", [])],
                needs_combination=plan_data.get("needs_combination", False),
                combination_strategy=plan_data.get("combination_strategy")
            )
            
            logger.info(
                f"查询计划生成成功: no_match={query_plan.no_data_source_match}, "
                f"use_temp_table={query_plan.use_temp_table}, "
                f"temp_table={query_plan.temp_table_name}, "
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
                    "use_temp_table": query_plan.use_temp_table,
                    "temp_table_name": query_plan.temp_table_name,
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
        prompt = """你是数据查询规划专家，根据用户查询生成执行计划。

可用数据源：

"""
        
        # 添加 session 临时表信息（如果有）
        if session_temp_tables:
            prompt += "## Session 临时表（历史查询结果）\n\n"
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
                prompt += f"### 数据库ID: {db_id}\n"
                prompt += f"名称: {schema.get('name', 'Unknown')}\n"
                prompt += f"类型: {schema.get('type', 'Unknown')}\n"
                prompt += "表结构:\n"
                tables = schema.get('tables', {})
                for table_name, columns in tables.items():
                    column_names = [col['name'] for col in columns]
                    prompt += f"  - {table_name}: {', '.join(column_names)}\n"
                prompt += "\n"
        
        # 添加MCP工具信息
        if mcp_tools:
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
        
        prompt += """
返回JSON格式：

{
  "no_data_source_match": false,
  "user_message": null,
  "use_temp_table": false,
  "temp_table_name": null,
  "sql_queries": [
    {
      "db_config_id": "数据库ID",
      "sql": "SQL查询语句",
      "source_alias": "结果别名"
    }
  ],
  "mcp_calls": [
    {
      "mcp_config_id": "MCP Server ID",
      "tool_name": "工具名称",
      "parameters": {"参数名": "参数值"},
      "source_alias": "结果别名"
    }
  ],
  "needs_combination": true/false,
  "combination_strategy": "组合策略说明（如需要）"
}

规则：
1. 判断用户查询是否与可用数据源相关：
   - 如果查询内容与所有数据源都无关，设置 no_data_source_match=true，user_message="抱歉，在当前配置的数据源中无法找到与您查询相关的信息"
   - 如果查询与数据源相关，设置 no_data_source_match=false，user_message=null

2. **智能判断是否使用临时表**：
   - 如果用户查询可以直接使用 session 临时表（历史查询结果）回答，设置 use_temp_table=true，temp_table_name="表名"
   - 例如："显示前10条"、"按某列排序"、"筛选某个条件"、"统计总数"等操作
   - 此时 sql_queries 和 mcp_calls 应为空数组
   - 如果需要新的数据查询，设置 use_temp_table=false

3. **重要：多步骤查询处理**：
   - 如果查询需要多个步骤，且后续步骤依赖前面步骤的结果，必须将所有逻辑合并到单个SQL查询中
   - **禁止**在 sql_queries 数组中的后续查询引用前面查询的 source_alias，因为这些别名不会自动创建为临时表
   - 使用 SQL 子查询（subquery）或 CTE（WITH 子句）来实现多步骤逻辑
   - 例如：查询"成绩最好的3个学生所在的院系"应该写成单个SQL：
     SELECT DISTINCT d.* 
     FROM Departments d 
     JOIN Courses c ON d.department_id = c.department_id 
     JOIN Course_Sections cs ON c.course_id = cs.course_id 
     JOIN Student_Enrollments se ON cs.section_id = se.section_id 
     JOIN (
       SELECT s.student_id 
       FROM Students s 
       JOIN Student_Enrollments se ON s.student_id = se.student_id 
       JOIN Exams e ON se.section_id = e.section_id 
       JOIN Exam_Scores es ON e.exam_id = es.exam_id 
       GROUP BY s.student_id 
       ORDER BY AVG(es.score) DESC 
       LIMIT 3
     ) AS top_students ON se.student_id = top_students.student_id

4. 当 no_data_source_match=true 时，sql_queries 和 mcp_calls 应为空数组
5. 只生成SELECT查询
6. 多数据源查询时设置needs_combination为true（仅当需要从不同数据库或MCP源组合数据时）
7. 计算字段和聚合函数必须使用 AS 指定别名（如 COUNT(*) AS total_count），别名使用小写字母和下划线，不要包含特殊字符
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
    ) -> ChartSuggestion:
        """
        分析数据元信息，推荐图表类型并生成总结
        
        注意：只接收元信息，不接收原始数据
        
        Args:
            query: 用户的原始查询
            metadata: 数据元信息（列名、类型、行数）
            model: 使用的模型（可选）
        
        Returns:
            ChartSuggestion对象，包含图表类型、配置和总结
        """
        model = model or self.default_model
        
        # 尝试从缓存获取
        cache = get_cache_service()
        cache_key = cache._generate_key(
            "chart_suggestion",
            {
                "query": query,
                "columns": metadata.columns,
                "column_types": metadata.column_types,
                "row_count": metadata.row_count,
                "model": model
            }
        )
        
        cached_result = cache.get(cache_key)
        if cached_result:
            logger.info(f"图表分析缓存命中: query='{query[:50]}...'")
            return ChartSuggestion(
                chart_type=cached_result["chart_type"],
                chart_config=cached_result["chart_config"],
                summary=cached_result["summary"]
            )
        
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
            
            # 保存到缓存
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
{
  "chart_type": "图表类型",
  "chart_config": {
    "title": {"text": "图表标题"},
    "tooltip": {"trigger": "axis"},
    "xAxis": {"type": "category", "data": "{{DATA_PLACEHOLDER_X}}"},
    "yAxis": {"type": "value"},
    "series": [{
      "name": "系列名称",
      "type": "图表类型",
      "data": "{{DATA_PLACEHOLDER}}"
    }]
  },
  "summary": "数据分析总结"
}

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
        model: str = None,
    ) -> SensitiveRule:
        """
        将自然语言转换为结构化的敏感信息规则
        
        Args:
            natural_language: 自然语言描述的规则
            available_columns: 可用的列名列表（可选）
            model: 使用的模型（可选）
        
        Returns:
            SensitiveRule对象
        """
        model = model or self.default_model
        
        logger.info(f"解析敏感信息规则: '{natural_language[:50]}...'")
        
        system_prompt = self._build_sensitive_rule_system_prompt(available_columns)
        
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
    
    def _build_sensitive_rule_system_prompt(
        self,
        available_columns: List[str] = None
    ) -> str:
        """构建敏感规则解析的系统提示"""
        prompt = """你是数据安全专家，将自然语言转换为敏感信息过滤规则。

处理模式：
- filter: 完全移除列
- mask: 脱敏处理

"""
        
        if available_columns:
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

规则：
1. 识别多种可能的列名（中文、英文、缩写）
2. 常见场景使用预定义模式
3. 特殊需求使用自定义规则
4. filter模式的pattern为null
5. 自定义规则必须是有效JSON字符串
"""
        
        return prompt
