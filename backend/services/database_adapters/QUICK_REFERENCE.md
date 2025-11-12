# 数据库适配器快速参考

## 添加新数据库的3个步骤

### 1️⃣ 创建适配器类

```python
# services/database_adapters/your_db.py
from typing import Dict, Any
from .base import DatabaseAdapter

class YourDBAdapter(DatabaseAdapter):
    def get_connection_string(self, config: Dict[str, Any]) -> str:
        # 返回 SQLAlchemy 连接字符串
        return f"driver://{config['username']}:{config['password']}@{config['url']}"
    
    def get_driver_name(self) -> str:
        # 返回驱动名称
        return "your_db+driver"
    
    def get_connect_args(self) -> Dict[str, Any]:
        # 返回连接参数（可选）
        return {}
    
    def format_identifier(self, name: str) -> str:
        # 返回格式化的标识符
        return f'"{name}"'  # 或 `{name}` 或 [{name}]
    
    def get_db_type(self) -> str:
        # 返回数据库类型
        return "your_db"
```

### 2️⃣ 注册适配器

```python
# services/database_adapters/factory.py
from .your_db import YourDBAdapter

_adapters = {
    "mysql": MySQLAdapter,
    "postgresql": PostgreSQLAdapter,
    "sqlite": SQLiteAdapter,
    "your_db": YourDBAdapter,  # 添加这行
}
```

### 3️⃣ 安装驱动

```bash
pip install your-db-driver
```

## 常见数据库驱动

| 数据库 | 驱动包 | 连接字符串格式 |
|--------|--------|---------------|
| Oracle | `cx_Oracle` | `oracle+cx_oracle://user:pass@host:1521/sid` |
| SQL Server | `pyodbc` | `mssql+pyodbc://user:pass@host/db?driver=...` |
| MariaDB | `pymysql` | `mysql+pymysql://user:pass@host:3306/db` |
| Snowflake | `snowflake-connector-python` | `snowflake://user:pass@account/db` |

## 标识符引用规则

| 数据库 | 引用符号 | 示例 |
|--------|---------|------|
| MySQL | 反引号 | `` `table_name` `` |
| PostgreSQL | 双引号 | `"table_name"` |
| SQL Server | 方括号 | `[table_name]` |
| Oracle | 双引号 | `"table_name"` |
| SQLite | 双引号 | `"table_name"` |

## LLM 自动适配

系统会在 prompt 中标注：`**类型: YOUR_DB**`

LLM 会自动生成对应的 SQL 方言，无需手动配置！

## 测试模板

```python
# tests/test_database_adapters.py
def test_your_db_adapter():
    adapter = DatabaseAdapterFactory.get_adapter("your_db")
    assert adapter.get_db_type() == "your_db"
    assert adapter.get_driver_name() == "your_db+driver"
    
    config = {
        'url': 'localhost:1234/testdb',
        'username': 'user',
        'password': 'pass'
    }
    conn_str = adapter.get_connection_string(config)
    assert "your_db+driver" in conn_str
```

## 前端UI更新（可选）

```jsx
// frontend/src/components/DatabaseConfigTab.jsx
<Select.Option value="your_db">Your Database</Select.Option>
```

```jsx
// 添加颜色标签
const colorMap = {
  sqlite: 'blue',
  mysql: 'green',
  postgresql: 'purple',
  your_db: 'orange',  // 添加这行
};
```

## 完整示例

查看现有适配器：
- `mysql.py` - 最简单的示例
- `postgresql.py` - 标准实现
- `sqlite.py` - 包含特殊连接参数

## 需要帮助？

- 📖 详细文档：[README.md](README.md)
- 🧪 测试示例：[../../tests/test_database_adapters.py](../../tests/test_database_adapters.py)
- 📝 更新日志：[CHANGELOG.md](CHANGELOG.md)
