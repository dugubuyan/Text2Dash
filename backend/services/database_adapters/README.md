# 数据库适配器

本模块使用适配器模式支持多种数据库类型，便于扩展新的数据库支持。

## 架构说明

```
database_adapters/
├── base.py       # 适配器基类（定义接口）
├── factory.py    # 适配器工厂（创建和管理实例）
├── mysql.py      # MySQL 适配器
├── postgresql.py # PostgreSQL 适配器
└── sqlite.py     # SQLite 适配器
```

## 当前支持的数据库

| 数据库 | 驱动 | 标识符引用 |
|--------|------|-----------|
| MySQL | `mysql+pymysql` | 反引号 `` `name` `` |
| PostgreSQL | `postgresql+psycopg2` | 双引号 `"name"` |
| SQLite | `sqlite` | 双引号 `"name"` |

## 如何添加新的数据库支持

### 示例：添加 Oracle 支持

**步骤1：创建适配器类** (`oracle.py`):

```python
from typing import Dict, Any
from .base import DatabaseAdapter

class OracleAdapter(DatabaseAdapter):
    def get_connection_string(self, config: Dict[str, Any]) -> str:
        username = config.get('username', '')
        password = config.get('password', '')
        url = config.get('url', '')
        return f"oracle+cx_oracle://{username}:{password}@{url}"
    
    def get_driver_name(self) -> str:
        return "oracle+cx_oracle"
    
    def get_connect_args(self) -> Dict[str, Any]:
        return {}
    
    def format_identifier(self, name: str) -> str:
        return f'"{name}"'
    
    def get_db_type(self) -> str:
        return "oracle"
```

**步骤2：注册适配器** (`factory.py`):

```python
from .oracle import OracleAdapter

_adapters = {
    "mysql": MySQLAdapter,
    "postgresql": PostgreSQLAdapter,
    "sqlite": SQLiteAdapter,
    "oracle": OracleAdapter,  # 添加这行
}
```

**步骤3：安装驱动**:

```bash
pip install cx_Oracle
```

**步骤4：更新前端UI**（可选）:

在 `frontend/src/components/DatabaseConfigTab.jsx` 中添加：
```jsx
<Select.Option value="oracle">Oracle</Select.Option>
```

**完成！** 系统会自动：
- 使用 Oracle 适配器构建连接字符串
- 在 LLM prompt 中标注 `**类型: ORACLE**`
- LLM 自动生成符合 Oracle SQL 方言的查询语句

## 适配器接口说明

所有适配器必须实现以下方法：

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `get_connection_string(config)` | 构建连接字符串 | SQLAlchemy 连接字符串 |
| `get_driver_name()` | 获取驱动名称 | 如 `"mysql+pymysql"` |
| `get_connect_args()` | 获取连接参数 | 参数字典 |
| `format_identifier(name)` | 格式化标识符 | 带引号的标识符 |
| `get_db_type()` | 获取数据库类型 | 如 `"mysql"` |

## 常见数据库驱动参考

| 数据库 | SQLAlchemy驱动 | Python包 |
|--------|---------------|----------|
| MySQL | `mysql+pymysql` | `pymysql` |
| PostgreSQL | `postgresql+psycopg2` | `psycopg2-binary` |
| SQLite | `sqlite` | 内置 |
| Oracle | `oracle+cx_oracle` | `cx_Oracle` |
| SQL Server | `mssql+pyodbc` | `pyodbc` |
| MariaDB | `mysql+pymysql` | `pymysql` |

## LLM 智能适配

系统会在 LLM prompt 中明确标注数据库类型（如 `**类型: MYSQL**`），LLM 会自动识别并生成对应的 SQL 方言。

**示例**：

用户查询："查询最近7天的订单"

- **MySQL**: `WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)`
- **PostgreSQL**: `WHERE created_at >= NOW() - INTERVAL '7 days'`
- **Oracle**: `WHERE created_at >= SYSDATE - 7`
- **SQL Server**: `WHERE created_at >= DATEADD(DAY, -7, GETDATE())`

无需手动维护 SQL 方言规范，LLM 会自动处理！
