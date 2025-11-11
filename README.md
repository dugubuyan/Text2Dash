# 商业报表生成器 (Business Report Generator)

基于自然语言的智能数据分析和可视化系统。用户通过自然语言描述需求，系统利用大语言模型（LLM）自动生成SQL查询、分析数据并生成可视化报表。

## 功能特性

- 🤖 自然语言查询转SQL
- 📊 智能图表类型推荐
- 🔒 敏感信息过滤和脱敏
- 💬 会话管理和上下文追问
- 📅 常用报表保存和定时执行
- 📄 多格式导出（PDF、Excel）
- 🔌 多数据源支持（数据库 + MCP Server）
- 🎨 基于React + Ant Design的现代化UI

## 技术栈

**前端：**
- React 18+ (Vite)
- Ant Design 5.x
- Echarts 5.x
- Axios

**后端：**
- Python 3.10+
- FastAPI
- LiteLLM (多模型支持)
- MCP (Model Context Protocol)
- mem0 (会话管理)
- SQLAlchemy + SQLite

## 项目结构

```
.
├── frontend/          # React前端应用
├── backend/           # FastAPI后端服务
├── data/              # SQLite数据库文件
├── logs/              # 日志文件
├── .env.example       # 环境变量模板
└── README.md          # 项目文档
```

## 快速开始

### 1. 环境准备

确保已安装：
- Node.js 18+ 和 npm
- Python 3.10+
- pip

### 2. 配置环境变量

复制环境变量模板并填入实际值：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入必要的配置：
- `LITELLM_API_KEY`: LLM API密钥
- `ENCRYPTION_KEY`: 数据加密密钥（可使用 `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` 生成）

### 3. 创建并激活Python虚拟环境

**创建虚拟环境：**
```bash
python -m venv venv
```

**激活虚拟环境：**

macOS/Linux:
```bash
source venv/bin/activate
```

Windows:
```bash
venv\Scripts\activate
```

### 4. 安装依赖

**后端：**
```bash
pip install -r backend/requirements.txt
```

**前端：**
```bash
cd frontend
npm install
```

### 5. 启动服务

**后端服务：**
```bash
python backend/main.py
```

后端将运行在 `http://localhost:8000`

**前端服务：**
```bash
cd frontend
npm run dev
```

前端将运行在 `http://localhost:5173` 或 `http://localhost:5174`

### 6. 访问应用

打开浏览器访问前端地址，开始使用商业报表生成器！

## 开发指南

### 后端开发

后端使用FastAPI框架，主要目录结构：
- `main.py`: 应用入口
- `services/`: 业务逻辑层
- `models/`: 数据模型
- `routes/`: API路由

### 前端开发

前端使用React + Vite，主要目录结构：
- `src/components/`: React组件
- `src/pages/`: 页面组件
- `src/services/`: API客户端
- `src/utils/`: 工具函数

## API文档

启动后端服务后，访问以下地址查看API文档：
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 测试

### 回归测试（推荐）

每次实现新功能后，运行回归测试确保系统整体正确性：

```bash
# 快速测试（推荐，用于日常开发）
./run_tests.sh --quick

# 默认测试（快速测试 + 数据库测试）
./run_tests.sh

# 完整测试（包括需要API的测试）
./run_tests.sh --full
```

或直接运行：
```bash
source venv/bin/activate
python backend/tests/run_all_tests.py --quick
```

详细测试文档请查看 [backend/tests/README.md](backend/tests/README.md)

### 运行单个测试

```bash
# 运行单个测试文件
python backend/tests/test_mcp_connector.py

# 运行pytest测试
pytest backend/tests/test_report_service.py -v
```

### 测试覆盖

- ✅ MCP连接器测试
- ✅ 敏感信息过滤服务测试
- ✅ 数据源管理器测试
- ✅ 数据库连接器测试
- ✅ LLM服务测试
- ✅ 会话管理器测试
- ✅ 报表服务测试
- ✅ 导出服务测试
- ✅ 端到端集成测试

## 部署

详细部署指南请参考设计文档中的部署架构章节。

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！
