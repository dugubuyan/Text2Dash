#!/bin/bash
# 数据库结构分析工具使用示例

echo "==================================="
echo "数据库结构分析工具 - 使用示例"
echo "==================================="
echo ""

# 示例 1: 分析本地 SQLite 配置数据库
echo "示例 1: 分析配置数据库"
python tools/db_schema_analyzer.py sqlite:///./data/config.db tools/config_db_schema.md
echo ""

# 示例 2: 如果你有其他数据库，可以这样使用
# echo "示例 2: 分析 PostgreSQL 数据库"
# python tools/db_schema_analyzer.py postgresql://user:password@localhost:5432/dbname tools/postgres_schema.md
# echo ""

# 示例 3: 分析 MySQL 数据库
# echo "示例 3: 分析 MySQL 数据库"
# python tools/db_schema_analyzer.py mysql+pymysql://user:password@localhost:3306/dbname tools/mysql_schema.md
# echo ""

echo "==================================="
echo "完成！查看生成的 Markdown 文件"
echo "=================================