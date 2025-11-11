# 数据库迁移：从数据快照到临时表方案

## 概述

这个迁移将数据存储方式从"保存前10条数据快照"改为"session 级临时表"，实现完整数据复用。

## 迁移内容

### 数据库变更

1. **删除表：** `report_snapshots`
2. **修改表：** `session_interactions` 添加 `temp_table_name` 字段

### 代码变更

- `backend/models/session.py` - 删除 ReportSnapshot 模型
- `backend/services/data_source_manager.py` - 添加临时表管理
- `backend/services/session_manager.py` - 使用临时表
- `backend/services/report_service.py` - 保存到临时表
- `backend/routes/sessions.py` - 从临时表查询
- `backend/services/llm_service.py` - 增强上下文

## 使用步骤

### 1. 测试迁移（推荐）

在测试数据库上验证迁移过程：

```bash
python backend/migrations/test_migration.py
```

### 2. 执行迁移

**⚠️ 重要：迁移前会自动备份数据库**

```bash
python backend/migrations/migrate_to_temp_tables.py
```

### 3. 验证结果

迁移脚本会自动验证：
- ✅ `report_snapshots` 表已删除
- ✅ `temp_table_name` 字段已添加
- ✅ 旧的临时表已清理

### 4. 重启服务

```bash
# 重启后端服务
cd backend
python main.py
```

### 5. 测试功能

1. 生成新报表
2. 查看历史记录
3. 点击历史记录加载数据
4. 在同一 session 中提问相关问题

## 回滚方法

如果迁移后出现问题，可以回滚到备份：

```bash
# 自动查找最新备份
python backend/migrations/migrate_to_temp_tables.py --rollback

# 或指定备份文件
python backend/migrations/migrate_to_temp_tables.py --rollback --backup data/app.db.backup_20241103_143000
```

## 自定义选项

### 指定数据库路径

```bash
python backend/migrations/migrate_to_temp_tables.py --db /path/to/your/database.db
```

### 查看帮助

```bash
python backend/migrations/migrate_to_temp_tables.py --help
```

## 迁移前后对比

### 迁移前

```
session_interactions
├── id
├── session_id
├── user_query
├── sql_query
├── chart_config
├── summary
└── created_at

report_snapshots
├── id
├── session_id
├── interaction_id
├── data_snapshot (JSON, 仅前10条)
└── created_at
```

### 迁移后

```
session_interactions
├── id
├── session_id
├── user_query
├── sql_query
├── chart_config
├── summary
├── temp_table_name (新增)
└── created_at

临时表 (动态创建)
session_{session_id}_interaction_{n}
├── 数据字段1
├── 数据字段2
└── ... (完整数据)
```

## 优势

1. **完整数据** - 保存所有查询结果，无数据丢失
2. **高性能** - 数据库原生查询，支持索引
3. **灵活查询** - 支持分页、过滤、聚合
4. **数据复用** - 同一 session 的查询可以复用历史数据
5. **简化代码** - 删除 JSON 序列化/反序列化逻辑

## 注意事项

1. **磁盘空间** - 临时表会占用更多空间
2. **清理机制** - Session 结束时会自动清理临时表
3. **备份重要** - 迁移前会自动备份，请妥善保管
4. **测试充分** - 建议先在测试环境验证

## 故障排除

### 问题：迁移失败

**解决：**
1. 检查数据库文件权限
2. 确保数据库未被其他进程占用
3. 查看错误信息
4. 使用 `--rollback` 恢复备份

### 问题：找不到数据库文件

**解决：**
1. 检查 `.env` 文件中的 `DATABASE_URL`
2. 使用 `--db` 参数指定路径

### 问题：备份文件太大

**解决：**
1. 迁移成功后可以删除备份
2. 或压缩备份文件：`gzip data/app.db.backup_*`

## 技术支持

如有问题，请查看：
- `SESSION_TEMP_TABLE_REFACTOR.md` - 详细设计文档
- 迁移脚本源码中的注释

---

**版本：** 1.0
**日期：** 2024-11-03
**状态：** 待执行
