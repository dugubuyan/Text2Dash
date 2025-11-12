# 商业报表生成器 - 后端服务

基于 FastAPI 的智能数据分析后端服务，支持自然语言查询、多数据源集成、敏感信息过滤和报表生成。

## 技术栈

- **框架**: FastAPI
- **ORM**: SQLAlchemy
- **LLM**: LiteLLM (支持多种模型)
- **数据协议**: MCP (Model Context Protocol)
- **会话管理**: mem0
- **加密**: cryptography (Fernet)
- **数据库**: SQLite

## 目录结构

```
backend/
├── main.py                    # FastAPI 应用入口
├── database.py                # 数据库管理
├── requirements.txt           # Python 依赖
│
├── models/                    # 数据模型
│   ├── database_config.py     # 数据库配置
│   ├── mcp_server_config.py   # MCP Server 配置
│   ├── sensitive_rule.py      # 敏感信息规则
│   ├── saved_report.py        # 常用报表
│   └── session.py             # 会话和交互
│
├── services/                  # 业务逻辑层
│   ├── llm_service.py         # LLM 服务
│   ├── database_connector.py  # 数据库连接器
│   ├── mcp_connector.py       # MCP 连接器
│   ├── data_source_manager.py # 数据源管理器
│   ├── filter_service.py      # 敏感信息过滤
│   ├── report_service.py      # 报表生成服务
│   ├── session_manager.py     # 会话管理
│   ├── export_service.py      # 导出服务
│   ├── cache_service.py       # 缓存服务
│   ├── encryption_service.py  # 加密服务
│   └── database_adapters/     # 数据库适配器
│       ├── base.py            # 适配器基类
│       ├── factory.py         # 适配器工厂
│       ├── mysql.py           # MySQL 适配器
│       ├── postgresql.py      # PostgreSQL 适配器
│       └── sqlite.py          # SQLite 适配器
│
├── routes/                    # API 路由
│   ├── databases.py           # 数据库配置 API
│   ├── mcp_servers.py         # MCP Server API
│   ├── sensitive_rules.py     # 敏感规则 API
│   ├── reports.py             # 报表生成 API
│   ├── sessions.py            # 会话管理 API
│   ├── export.py              # 导出 API
│   └── cache.py               # 缓存 API
│
├── utils/                     # 工具函数
│   ├── logger.py              # 日志配置
│   ├── datetime_helper.py     # 日期时间工具
│   └── db_monitor.py          # 数据库监控
│
├── migrations/                # 数据库迁移
│   └── migrate_to_temp_tables.py
│
└── tests/                     # 测试套件
    ├── run_all_tests.py       # 回归测试运行器
    └── test_*.py              # 各模块测试
```

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 到 `.env` 并配置：

```bash
# LLM API 配置
GEMINI_API_KEY=your_gemini_api_key
# 或
OPENAI_API_KEY=your_openai_api_key

# 加密密钥（使用以下命令生成）
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=your_encryption_key

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=./logs/app.log
```

### 3. 初始化数据库

```bash
python -m backend.database
```

### 4. 启动服务

```bash
python backend/main.py
```

服务将运行在 `http://localhost:8000`

### 5. 查看 API 文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 核心功能

### 1. 自然语言查询

通过 LLM 将自然语言转换为 SQL 查询或 MCP 工具调用：

```python
POST /api/reports/generate
{
  "query": "显示2023年所有学生的平均成绩",
  "data_source_ids": ["db-001"],
  "session_id": "session-123"
}
```

### 2. 多数据源支持

- **数据库**: MySQL, PostgreSQL, SQLite（使用适配器模式，易于扩展）
- **MCP Server**: 通过 Model Context Protocol 连接外部数据源

#### 数据库适配器架构

系统使用适配器模式支持多种数据库类型。当前支持 MySQL、PostgreSQL、SQLite，添加新数据库只需3步：创建适配器类、注册适配器、安装驱动。

系统会自动在 LLM prompt 中标注数据库类型（如 `**类型: MYSQL**`），LLM 会自动生成符合该数据库 SQL 方言的查询语句。

详细文档：[database_adapters/README.md](services/database_adapters/README.md)

### 3. 敏感信息过滤

支持多种脱敏模式：
- **filter**: 完全移除敏感列
- **mask**: 脱敏处理（手机号、邮箱、身份证等）
- **自定义规则**: JSON 格式的灵活配置

### 4. 会话管理

- 上下文追问
- 会话历史
- 自动压缩（使用 LLM）
- 临时表支持

### 5. 报表导出

- PDF 格式（包含图表和数据表）
- Excel 格式（多工作表）

### 6. 缓存优化

- Schema 缓存
- MCP 工具列表缓存
- 查询结果缓存

## 测试

### 运行回归测试

```bash
# 快速测试（推荐，用于日常开发）
./run_tests.sh --quick

# 默认测试（快速测试 + 数据库测试）
./run_tests.sh

# 完整测试（包括需要 API 的测试）
./run_tests.sh --full
```

### 运行单个测试

```bash
# 运行单个测试文件
python backend/tests/test_mcp_connector.py

# 运行 pytest 测试
pytest backend/tests/test_report_service.py -v
```

详细测试文档请查看 [tests/README.md](tests/README.md)

## API 端点

### 数据库配置
- `GET /api/databases` - 获取所有数据库配置
- `POST /api/databases` - 创建数据库配置
- `PUT /api/databases/{id}` - 更新数据库配置
- `DELETE /api/databases/{id}` - 删除数据库配置
- `POST /api/databases/{id}/test` - 测试数据库连接
- `GET /api/databases/{id}/schema` - 获取数据库 Schema

### MCP Server 配置
- `GET /api/mcp-servers` - 获取所有 MCP Server
- `POST /api/mcp-servers` - 创建 MCP Server
- `PUT /api/mcp-servers/{id}` - 更新 MCP Server
- `DELETE /api/mcp-servers/{id}` - 删除 MCP Server
- `POST /api/mcp-servers/{id}/test` - 测试 MCP 连接
- `GET /api/mcp-servers/{id}/tools` - 获取可用工具

### 敏感信息规则
- `GET /api/sensitive-rules` - 获取所有规则
- `POST /api/sensitive-rules` - 创建规则
- `PUT /api/sensitive-rules/{id}` - 更新规则
- `DELETE /api/sensitive-rules/{id}` - 删除规则
- `POST /api/sensitive-rules/parse` - 解析自然语言规则

### 报表生成
- `POST /api/reports/generate` - 生成报表
- `GET /api/reports/saved` - 获取常用报表列表
- `POST /api/reports/saved` - 保存常用报表
- `POST /api/reports/saved/{id}/run` - 执行常用报表
- `DELETE /api/reports/saved/{id}` - 删除常用报表

### 会话管理
- `POST /api/sessions` - 创建会话
- `GET /api/sessions/{id}` - 获取会话信息
- `GET /api/sessions/{id}/history` - 获取会话历史
- `DELETE /api/sessions/{id}` - 删除会话

### 导出
- `POST /api/export/pdf` - 导出为 PDF
- `POST /api/export/excel` - 导出为 Excel

### 缓存
- `DELETE /api/cache/schema/{db_id}` - 清除 Schema 缓存
- `DELETE /api/cache/mcp-tools/{mcp_id}` - 清除 MCP 工具缓存
- `DELETE /api/cache/all` - 清除所有缓存

## 开发指南

### 添加新的数据库支持

系统使用适配器模式支持多种数据库。添加新数据库只需3步：

1. 创建适配器类（实现 `DatabaseAdapter` 接口）
2. 在工厂中注册适配器
3. 安装对应的数据库驱动

系统会自动在 LLM prompt 中标注数据库类型，LLM 会自动生成对应的 SQL 方言。

详细文档和示例：[database_adapters/README.md](services/database_adapters/README.md)

### 添加新的 API 端点

1. 在 `routes/` 目录创建或编辑路由文件
2. 在 `main.py` 中注册路由
3. 添加相应的测试

### 添加新的服务

1. 在 `services/` 目录创建服务文件
2. 实现业务逻辑
3. 在 `services/__init__.py` 中导出
4. 添加单元测试

### 数据库迁移

```bash
# 运行迁移脚本
python backend/migrations/migrate_to_temp_tables.py

# 测试迁移
python backend/migrations/test_migration.py
```

## 性能优化

- **缓存**: Schema 和工具列表缓存，减少重复查询
- **并行查询**: 多数据源并行执行
- **临时表**: 使用 SQLite 临时表进行数据组合
- **连接池**: 数据库连接池管理

## 安全性

- **加密**: 敏感信息使用 Fernet 加密存储
- **环境变量**: API 密钥通过环境变量管理
- **敏感信息过滤**: 自动过滤和脱敏敏感数据
- **输入验证**: Pydantic 模型验证

## 故障排查

### 问题：ModuleNotFoundError
**解决方案**: 确保虚拟环境已激活并安装了所有依赖

### 问题：数据库连接失败
**解决方案**: 检查数据库配置和网络连接

### 问题：LLM API 调用失败
**解决方案**: 检查 API 密钥配置和网络连接

### 问题：测试失败
**解决方案**: 运行 `./check_git_status.sh` 检查环境

## 相关文档

- [数据库适配器文档](services/database_adapters/README.md) - 如何添加新数据库支持
- [服务层文档](services/README.md)
- [测试文档](tests/README.md)
- [迁移文档](migrations/README.md)

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License
