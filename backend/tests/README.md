# 测试套件

## 目录结构

```
backend/tests/
├── __init__.py                    # 测试包初始化
├── README.md                      # 本文件
├── run_all_tests.py              # 回归测试运行器 ⭐
│
├── test_mcp_connector.py         # MCP连接器测试
├── test_filter_service.py        # 敏感信息过滤服务测试
├── test_data_source_manager.py   # 数据源管理器测试
├── test_database_connector.py    # 数据库连接器测试
├── test_infrastructure.py        # 基础设施测试
├── test_llm_service.py           # LLM服务测试
├── test_session_manager.py       # 会话管理器测试
├── test_report_service.py        # 报表服务测试 (pytest)
├── test_export_service.py        # 导出服务测试 (pytest)
├── test_e2e_integration.py       # 端到端集成测试 (pytest)
├── test_session_temp_table.py    # Session临时表测试
├── test_sensitive_rule_e2e.py    # 敏感规则端到端测试
└── test_performance.py           # 性能测试
```

## 快速开始

### 1. 激活虚拟环境

```bash
source venv/bin/activate
```

### 2. 运行回归测试

```bash
# 运行快速测试（推荐，用于日常开发）
python backend/tests/run_all_tests.py --quick

# 运行默认测试（快速测试 + 数据库测试）
python backend/tests/run_all_tests.py

# 运行所有测试（包括需要API的测试）
python backend/tests/run_all_tests.py --full
```

## 测试分类

### 🚀 快速测试（无外部依赖）
这些测试不需要数据库、API密钥等外部依赖，运行速度快，适合频繁运行。

- **test_mcp_connector.py** - MCP连接器数据格式验证和元信息提取
- **test_filter_service.py** - 敏感信息过滤和脱敏功能
- **test_data_source_manager.py** - 数据源管理和临时表操作

```bash
python backend/tests/run_all_tests.py --quick
```

### 💾 数据库测试
需要配置数据库，测试数据库相关功能。

- **test_database_connector.py** - 数据库连接、查询、Schema获取
- **test_infrastructure.py** - 数据库、加密、日志等基础设施

### 🤖 API测试
需要配置 LLM API 密钥（GEMINI_API_KEY 或 OPENAI_API_KEY）。

- **test_llm_service.py** - LLM服务和敏感规则解析
- **test_session_manager.py** - 会话管理和上下文压缩
- **test_sensitive_rule_e2e.py** - 从自然语言到数据脱敏的完整流程

### 🧪 Pytest测试
使用 pytest 框架的单元测试。

- **test_report_service.py** - 报表生成服务（使用mock）
- **test_export_service.py** - PDF和Excel导出功能

### 🔗 集成测试
测试完整的业务流程。

- **test_e2e_integration.py** - 端到端集成测试
- **test_session_temp_table.py** - Session临时表功能测试

### ⚡ 性能测试
分析各组件的性能表现。

- **test_performance.py** - 性能分析和优化建议

## 运行单个测试

```bash
# 运行单个测试文件
python backend/tests/test_mcp_connector.py

# 运行pytest测试
pytest backend/tests/test_report_service.py -v
pytest backend/tests/test_export_service.py -v
```

## 测试覆盖

| 模块 | 测试文件 | 覆盖率 | 状态 |
|------|---------|--------|------|
| MCP连接器 | test_mcp_connector.py | ✅ 完整 | 通过 |
| 过滤服务 | test_filter_service.py | ✅ 完整 | 通过 |
| 数据源管理器 | test_data_source_manager.py | ✅ 完整 | 通过 |
| 数据库连接器 | test_database_connector.py | ✅ 完整 | 需要数据库 |
| LLM服务 | test_llm_service.py | ✅ 完整 | 需要API |
| 会话管理器 | test_session_manager.py | ✅ 完整 | 需要API |
| 报表服务 | test_report_service.py | ✅ 完整 | 通过 |
| 导出服务 | test_export_service.py | ✅ 完整 | 通过 |
| 基础设施 | test_infrastructure.py | ✅ 完整 | 需要数据库 |

## 环境要求

### 必需
- Python 3.8+
- 虚拟环境已激活
- 已安装依赖：`pip install -r requirements.txt`

### 可选（用于完整测试）
- 测试数据库：`data/test_medical.db`
- LLM API密钥：在 `.env` 文件中配置
  ```
  GEMINI_API_KEY=your_key_here
  # 或
  OPENAI_API_KEY=your_key_here
  ```

## 持续集成建议

### 开发阶段
每次实现新功能后运行快速测试：
```bash
python backend/tests/run_all_tests.py --quick
```

### 提交前
运行默认测试确保核心功能正常：
```bash
python backend/tests/run_all_tests.py
```

### 发布前
运行完整测试套件：
```bash
python backend/tests/run_all_tests.py --full
```

## 故障排查

### 问题：ModuleNotFoundError
**解决方案**：确保虚拟环境已激活
```bash
source venv/bin/activate
```

### 问题：测试超时
**解决方案**：检查网络连接（API测试）或数据库连接

### 问题：API测试失败
**解决方案**：检查 `.env` 文件中的API密钥配置

### 问题：数据库测试失败
**解决方案**：运行 `python data/init_database.py` 创建测试数据库

## 添加新测试

1. 在 `backend/tests/` 目录下创建新的测试文件
2. 文件名以 `test_` 开头
3. 在 `run_all_tests.py` 中添加到相应的测试组
4. 运行测试验证

## 测试最佳实践

1. **保持测试独立**：每个测试应该能独立运行
2. **清理测试数据**：测试结束后清理临时文件和数据
3. **使用Mock**：对外部依赖使用Mock以提高测试速度
4. **明确的断言**：使用清晰的断言消息
5. **快速反馈**：优先运行快速测试

## 贡献指南

添加新功能时，请：
1. 编写相应的单元测试
2. 运行回归测试确保没有破坏现有功能
3. 更新测试文档

---

**最后更新**: 2024-11-11
