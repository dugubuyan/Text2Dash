# 服务层文档

## LLM服务 (LLMService)

LLM服务是商业报表生成器的核心组件，负责所有与大语言模型的交互。

### 功能概述

1. **查询计划生成** - 将自然语言转换为SQL查询和MCP工具调用
2. **数据组合SQL生成** - 生成用于组合多数据源的SQL语句
3. **图表分析和推荐** - 根据数据元信息推荐图表类型并生成Echarts配置
4. **会话摘要压缩** - 压缩会话历史以防止上下文爆炸
5. **敏感信息规则解析** - 将自然语言转换为结构化的过滤规则

### 使用示例

```python
from backend.services import LLMService, DataMetadata, ConversationMessage

# 初始化服务
llm_service = LLMService()

# 1. 生成查询计划
query_plan = await llm_service.generate_query_plan(
    query="显示2023年所有学生的平均成绩",
    db_schemas={
        "db1": {
            "name": "学生数据库",
            "type": "sqlite",
            "tables": [
                {"name": "students", "columns": ["id", "name", "grade"]},
                {"name": "scores", "columns": ["student_id", "subject", "score"]}
            ]
        }
    },
    mcp_tools={},
    context=[]
)

# 2. 生成数据组合SQL
combination_sql = await llm_service.generate_combination_sql(
    query="合并学生信息和成绩数据",
    temp_table_info={
        "temp_students": {
            "columns": {"id": "INTEGER", "name": "TEXT"},
            "row_count": 100,
            "source": "database_1"
        },
        "temp_scores": {
            "columns": {"student_id": "INTEGER", "score": "REAL"},
            "row_count": 500,
            "source": "database_1"
        }
    }
)

# 3. 分析数据并推荐图表
metadata = DataMetadata(
    columns=["name", "average_score"],
    column_types={"name": "string", "average_score": "float"},
    row_count=100
)

chart_suggestion = await llm_service.analyze_data_and_suggest_chart(
    query="显示学生平均成绩",
    metadata=metadata
)

print(f"推荐图表类型: {chart_suggestion.chart_type}")
print(f"图表配置: {chart_suggestion.chart_config}")
print(f"分析总结: {chart_suggestion.summary}")

# 4. 压缩会话历史
messages = [
    ConversationMessage(role="user", content="显示学生信息"),
    ConversationMessage(role="assistant", content="已生成学生信息报表"),
    ConversationMessage(role="user", content="再显示成绩信息"),
    ConversationMessage(role="assistant", content="已生成成绩信息报表"),
]

summary = await llm_service.summarize_conversation(messages)
print(f"会话摘要: {summary}")

# 5. 解析敏感信息规则
sensitive_rule = await llm_service.parse_sensitive_rule(
    natural_language="隐藏学生的身份证号和手机号",
    available_columns=["id", "name", "id_card", "phone", "email"]
)

print(f"规则名称: {sensitive_rule.name}")
print(f"处理模式: {sensitive_rule.mode}")
print(f"影响列: {sensitive_rule.columns}")
```

### 配置

LLM服务通过环境变量配置：

```bash
# .env 文件
DEFAULT_MODEL=gemini/gemini-2.0-flash-exp
LITELLM_VERBOSE=False
LITELLM_API_KEY=your_api_key_here
```

### 错误处理

LLM服务实现了自动重试机制：
- 最大重试次数: 3次
- 重试策略: 指数退避
- 所有错误都会被记录到日志

### 注意事项

1. **数据隐私**: `analyze_data_and_suggest_chart` 方法只接收数据元信息，不接收原始数据
2. **Token使用**: 所有LLM调用都会记录token使用情况
3. **JSON响应**: 大部分方法要求LLM返回JSON格式，确保响应可解析
4. **上下文管理**: `generate_query_plan` 只使用最近5条会话消息作为上下文

## 数据传输对象 (DTOs)

### DataMetadata
数据元信息，包含列名、类型和行数。

### QueryPlan
查询计划，包含SQL查询和MCP工具调用列表。

### ChartSuggestion
图表建议，包含图表类型、Echarts配置和分析总结。

### SensitiveRule
敏感信息规则，定义如何处理敏感数据。

### ConversationMessage
会话消息，用于上下文管理。

## 测试

运行测试脚本验证LLM服务：

```bash
source venv/bin/activate
python backend/test_llm_service.py
```
