# 数据库配置管理指南

## 问题说明

在开发和测试过程中，数据库配置的 ID 可能会变成 UUID 格式，导致测试代码中硬编码的 `test-db-001` ID 无法找到配置。

## 解决方案

### 方案1：使用重置脚本（推荐）

运行重置脚本将配置ID恢复为固定的 `test-db-001`：

```bash
source venv/bin/activate
python backend/reset_test_db_config.py
```

### 方案2：手动重置

```bash
source venv/bin/activate
python << 'EOF'
from backend.database import get_database
from backend.models.database_config import DatabaseConfig

db = get_database()
with db.get_session() as session:
    # 删除旧配置
    session.query(DatabaseConfig).delete()
    
    # 创建新配置
    test_config = DatabaseConfig(
        id="test-db-001",
        name="测试医学院数据库",
        type="sqlite",
        url="sqlite:///./data/test_medical.db"
    )
    session.add(test_config)
    session.commit()
    print("✓ 配置已重置")
EOF
```

### 方案3：查看并使用现有UUID

如果不想重置，可以查看当前的UUID并更新测试代码：

```bash
python -c "
from backend.database import get_database
from backend.models.database_config import DatabaseConfig

db = get_database()
with db.get_session() as session:
    configs = session.query(DatabaseConfig).all()
    for config in configs:
        print(f'ID: {config.id}')
        print(f'名称: {config.name}')
"
```

然后在测试代码中使用这个UUID。

## 最佳实践

### 开发环境

使用固定的 ID（如 `test-db-001`）方便测试和开发：

```python
test_config = DatabaseConfig(
    id="test-db-001",  # 固定ID
    name="测试医学院数据库",
    type="sqlite",
    url="sqlite:///./data/test_medical.db"
)
```

### 生产环境

使用 UUID 确保唯一性：

```python
import uuid

prod_config = DatabaseConfig(
    id=str(uuid.uuid4()),  # 自动生成UUID
    name="生产数据库",
    type="postgresql",
    url="postgresql://..."
)
```

## 相关文件

- `backend/reset_test_db_config.py` - 重置脚本
- `backend/models/database_config.py` - 数据库配置模型
- `backend/database.py` - 数据库连接管理
- `data/config.db` - SQLite配置数据库文件

## 常见问题

### Q: 为什么ID会变成UUID？

A: 某些代码路径（如API创建配置）会自动生成UUID作为ID，而测试代码使用固定ID。

### Q: 如何避免这个问题？

A: 
1. 在测试前运行重置脚本
2. 使用 pytest fixtures 自动管理测试配置
3. 在测试代码中动态查询配置而不是硬编码ID

### Q: 重置会影响其他配置吗？

A: 当前的重置脚本只删除名称包含"测试"的配置，不会影响其他配置。如果需要保留所有配置，可以修改脚本只更新特定ID的配置。

## 验证配置

运行以下命令验证配置是否正确：

```bash
python -c "
from backend.database import get_database
from backend.models.database_config import DatabaseConfig

db = get_database()
with db.get_session() as session:
    config = session.query(DatabaseConfig).filter_by(id='test-db-001').first()
    if config:
        print('✓ test-db-001 配置存在')
        print(f'  名称: {config.name}')
        print(f'  类型: {config.type}')
    else:
        print('✗ test-db-001 配置不存在，请运行重置脚本')
"
```
