# 执行器模块使用指南

## 概述

执行器模块采用**策略模式**实现不同的报表生成路径。每个执行器负责处理特定的业务场景，使代码更加模块化和可维护。

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    ReportService                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  generate_report()                                     │  │
│  │    1. 获取上下文                                        │  │
│  │    2. 智能路由决策 (LLM)                               │  │
│  │    3. 选择执行器                                        │  │
│  │    4. 执行并返回结果                                    │  │
│  └───────────────────────────────────────────────────────┘  │
│                           │                                  │
│                           ▼                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Executor Selection                        │  │
│  │  executors = {                                         │  │
│  │    'direct_conversation': ConversationExecutor,       │  │
│  │    'reuse_data_regenerate_chart': ReuseDataExecutor,  │  │
│  │    'query_temp_table_with_chart': TempTableExecutor,  │  │
│  │    'query_new_data_with_chart': FullQueryExecutor,    │  │
│  │    'query_data_only': DataOnlyExecutor,               │  │
│  │  }                                                     │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 执行器列表

### 1. ConversationExecutor（对话执行器）

**文件**: `conversation.py`  
**Action**: `direct_conversation`, `clarify_and_guide`  
**用途**: 处理纯对话场景，不涉及数据查询

#### 使用场景
- 用户问候："你好"、"谢谢"
- 闲聊："今天天气怎么样"
- 需求不明确，需要引导用户

#### 特点
- ❌ 不查询数据
- ❌ 不生成图表
- ✅ 直接返回文本回复
- ✅ 可以提供建议列表

#### 示例
```python
# 输入
query = "你好"
action = "direct_conversation"
response = "你好！我可以帮你查询数据和生成报表。"

# 输出
ReportResult(
    chart_config={"type": "text"},
    summary="你好！我可以帮你查询数据和生成报表。",
    data=[],
    sql_query=None
)
```

---

### 2. ReuseDataExecutor（复用数据执行器）

**文件**: `reuse_data.py`  
**Action**: `reuse_data_regenerate_chart`  
**用途**: 复用上次查询的数据，重新生成图表配置

#### 使用场景
- 修改图表类型："换成柱状图"、"改成饼图"
- 修改图表配置："x轴改为名字"、"显示百分比"
- 不需要重新查询数据的场景

#### 特点
- ❌ 不查询源数据库
- ✅ 从临时表读取数据
- ✅ 重新生成图表配置
- ✅ 复用原有临时表

#### 流程
```
1. 获取上次交互的临时表名
2. 从临时表读取数据
3. 应用敏感信息过滤
4. 调用LLM生成新图表配置
5. 保存交互（复用临时表）
```

#### 示例
```python
# 第一次查询
query1 = "查询销售数据"
→ FullQueryExecutor
→ 创建临时表: temp_session123_1

# 第二次查询（复用数据）
query2 = "换成柱状图"
→ ReuseDataExecutor
→ 从 temp_session123_1 读取数据
→ 生成新图表配置
→ 复用 temp_session123_1
```

---

### 3. TempTableQueryExecutor（临时表查询执行器）

**文件**: `temp_table_query.py`  
**Action**: `query_temp_table_with_chart`  
**用途**: 查询临时表（筛选、排序等），生成新图表

#### 使用场景
- 数据筛选："只看销售额大于1000的"
- 数据排序："按销售额降序排列"
- 数据聚合："按地区汇总"
- 基于已有数据的二次查询

#### 特点
- ❌ 不查询源数据库
- ✅ 查询临时表（生成新SQL）
- ✅ 生成图表配置
- ❌ 不创建新临时表（数据来自已有临时表）

#### 流程
```
1. 获取session的临时表信息
2. 调用LLM生成查询计划（只针对临时表）
3. 执行查询
4. 应用敏感信息过滤
5. 生成图表配置
6. 保存交互（不创建新临时表）
```

#### 示例
```python
# 第一次查询
query1 = "查询所有销售数据"
→ FullQueryExecutor
→ 创建临时表: temp_session123_1 (1000条记录)

# 第二次查询（筛选）
query2 = "只看销售额大于1000的"
→ TempTableQueryExecutor
→ 生成SQL: SELECT * FROM temp_session123_1 WHERE sales > 1000
→ 执行查询 (返回200条记录)
→ 生成图表
→ 不创建新临时表
```

---

### 4. FullQueryExecutor（完整查询执行器）

**文件**: `full_query.py`  
**Action**: `query_new_data_with_chart`  
**用途**: 执行完整的查询流程（查询新数据 + 生成图表）

#### 使用场景
- 首次查询："查询本月销售数据"
- 查询不同数据源："查询用户表"
- 需要重新查询源数据库的场景

#### 特点
- ✅ 查询源数据库
- ✅ 支持多数据源组合
- ✅ 生成图表配置
- ✅ 创建临时表（供后续复用）

#### 流程
```
1. 获取数据源schema和临时表信息
2. 调用LLM生成查询计划
3. 执行查询计划（可能包含多个SQL和MCP调用）
4. 组合数据（如需要）
5. 应用敏感信息过滤
6. 生成图表配置
7. 创建临时表
8. 保存交互
```

#### 示例
```python
query = "查询本月销售数据"
→ FullQueryExecutor
→ 生成SQL: SELECT * FROM sales WHERE month = '2024-11'
→ 执行查询
→ 创建临时表: temp_session123_1
→ 生成图表
→ 返回完整报表
```

---

### 5. DataOnlyExecutor（仅数据执行器）

**文件**: `data_only.py`  
**Action**: `query_data_only`  
**用途**: 只查询数据，不生成图表（用于数据导出等场景）

#### 使用场景
- 数据导出："导出用户列表"
- 查看原始数据："给我看看销售数据"
- 不需要可视化的场景

#### 特点
- ✅ 查询源数据库
- ✅ 支持多数据源组合
- ❌ 不调用LLM生成图表
- ✅ 创建临时表
- ✅ 默认使用表格展示

#### 流程
```
1. 获取数据源schema和临时表信息
2. 调用LLM生成查询计划
3. 执行查询计划
4. 组合数据（如需要）
5. 应用敏感信息过滤
6. 生成简单摘要（不调用LLM）
7. 创建临时表
8. 保存交互
```

#### 示例
```python
query = "导出用户列表"
→ DataOnlyExecutor
→ 生成SQL: SELECT * FROM users
→ 执行查询
→ 创建临时表: temp_session123_1
→ 返回数据（chart_config={"type": "table"}）
```

---

## 执行器选择逻辑

智能路由（`smart_route`）根据以下因素决定使用哪个执行器：

### 决策因素
1. **用户意图**：查询数据、修改图表、闲聊等
2. **上下文**：是否有上次交互、是否有临时表
3. **数据源匹配**：用户需求是否匹配可用数据源

### 决策流程

```
用户查询
    │
    ▼
智能路由分析
    │
    ├─ 闲聊/不匹配 ──────────────────────► ConversationExecutor
    │
    ├─ 需要引导 ──────────────────────────► ConversationExecutor
    │
    ├─ 修改图表（有数据）─────────────────► ReuseDataExecutor
    │
    ├─ 筛选/排序（有临时表）──────────────► TempTableQueryExecutor
    │
    ├─ 查询新数据（需要图表）─────────────► FullQueryExecutor
    │
    └─ 查询新数据（不需要图表）───────────► DataOnlyExecutor
```

## 性能对比

| 执行器 | 数据库查询 | LLM调用 | 临时表操作 | 适用场景 |
|--------|-----------|---------|-----------|---------|
| Conversation | 0 | 1 | 无 | 闲聊 |
| ReuseData | 0 | 1 | 读取 | 改图表 |
| TempTable | 0 | 2 | 读取 | 筛选数据 |
| FullQuery | 1+ | 2-3 | 创建 | 查新数据 |
| DataOnly | 1+ | 1 | 创建 | 导出数据 |

## 扩展新执行器

### 步骤1：创建执行器类

```python
# backend/services/executors/my_executor.py
from .base import BaseExecutor

class MyExecutor(BaseExecutor):
    async def execute(self, query, session_id, model, **kwargs):
        # 实现你的逻辑
        pass
```

### 步骤2：注册执行器

```python
# backend/services/executors/__init__.py
from .my_executor import MyExecutor

__all__ = [..., 'MyExecutor']
```

### 步骤3：在ReportService中注册

```python
# backend/services/report_service.py
self.executors = {
    ...
    'my_action': MyExecutor(self),
}
```

### 步骤4：更新智能路由

```python
# backend/services/llm_service.py
# 在 _build_smart_router_prompt 中添加新的action描述
```

## 最佳实践

### 1. 错误处理

每个执行器都应该处理错误并提供降级策略：

```python
try:
    # 执行主逻辑
    result = await self.do_something()
except Exception as e:
    logger.error(f"执行失败: {e}")
    # 降级到其他执行器
    from .full_query import FullQueryExecutor
    executor = FullQueryExecutor(self.report_service)
    return await executor.execute(...)
```

### 2. 日志记录

使用统一的日志格式：

```python
logger.info(f"执行器开始: query='{query[:50]}...', session={session_id}")
logger.debug(f"中间状态: data_rows={len(data)}")
logger.info(f"执行器完成: interaction_id={interaction_id}")
```

### 3. 性能优化

- 使用 `asyncio.create_task()` 异步保存会话
- 避免不必要的LLM调用
- 复用临时表数据

### 4. 测试

为每个执行器编写单元测试：

```python
async def test_reuse_data_executor():
    executor = ReuseDataExecutor(report_service)
    result = await executor.execute(
        query="换成柱状图",
        session_id="test",
        data_source_ids=["db1"],
        context=[],
        model="gemini/gemini-2.0-flash"
    )
    assert result.chart_config["type"] == "bar"
```

## 常见问题

### Q1: 如何选择合适的执行器？

A: 不需要手动选择，智能路由会自动分析用户意图并选择最合适的执行器。

### Q2: 执行器之间可以互相调用吗？

A: 可以。例如 `ReuseDataExecutor` 在找不到临时表时会降级到 `FullQueryExecutor`。

### Q3: 如何调试执行器？

A: 查看日志中的 `智能路由决策: action=xxx` 来确认使用了哪个执行器。

### Q4: 执行器的性能如何监控？

A: 可以在每个执行器的 `execute()` 方法中添加性能监控代码：

```python
import time
start_time = time.time()
# ... 执行逻辑
duration = time.time() - start_time
logger.info(f"执行器耗时: {duration:.2f}s")
```

## 总结

执行器模块通过策略模式实现了：

✅ **职责分离**：每个执行器只处理一种场景  
✅ **易于扩展**：新增场景只需添加新执行器  
✅ **性能优化**：不同场景采用不同策略  
✅ **代码复用**：通过基类和工具函数避免重复  
✅ **易于测试**：可以单独测试每个执行器  

这种设计使得代码更加模块化、可维护，为后续功能扩展奠定了坚实的基础。
