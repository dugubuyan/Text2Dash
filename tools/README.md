# 数据库工具集

## db_schema_analyzer.py - 数据库结构分析工具

### 功能说明

这个工具可以连接到任何支持 SQLAlchemy 的数据库，自动分析所有表结构，并生成一个 AI 可读的 Markdown 文档。文档包含：

- 所有表的结构信息（字段、类型、约束等）
- 表的用途分析
- 数据内容说明
- 外键关系
- 索引信息
- 可用的查询操作建议（类似 Function Call 描述）

### 安装依赖

```bash
pip install sqlalchemy
```

根据你的数据库类型，可能还需要安装相应的驱动：

```bash
# PostgreSQL
pip install psycopg2-binary

# MySQL
pip install pymysql

# SQLite (Python内置，无需安装)
```

### 使用方法

#### 基本用法

```bash
python tools/db_schema_analyzer.py <database_url>
```

#### 指定输出文件

```bash
python tools/db_schema_analyzer.py <database_url> <output_file.md>
```

### 数据库URL格式

#### SQLite
```bash
python tools/db_schema_analyzer.py sqlite:///./data/config.db
python tools/db_schema_analyzer.py sqlite:///path/to/database.db
```

#### PostgreSQL
```bash
python tools/db_schema_analyzer.py postgresql://user:password@localhost:5432/dbname
python tools/db_schema_analyzer.py postgresql://user:password@host:port/database
```

#### MySQL
```bash
python tools/db_schema_analyzer.py mysql+pymysql://user:password@localhost:3306/dbname
```

#### SQL Server
```bash
python tools/db_schema_analyzer.py mssql+pyodbc://user:password@host/dbname?driver=ODBC+Driver+17+for+SQL+Server
```

### 使用示例

#### 示例 1: 分析本地 SQLite 数据库

```bash
python tools/db_schema_analyzer.py sqlite:///./data/config.db
```

输出文件：`db_schema_analysis_config.md`

#### 示例 2: 分析远程 PostgreSQL 数据库

```bash
python tools/db_schema_analyzer.py postgresql://admin:secret@db.example.com:5432/medical_school
```

输出文件：`db_schema_analysis_medical_school.md`

#### 示例 3: 自定义输出文件名

```bash
python tools/db_schema_analyzer.py sqlite:///./data/config.db my_database_schema.md
```

输出文件：`my_database_schema.md`

### 生成的文档内容

生成的 Markdown 文档包含以下部分：

1. **文档头部**
   - 生成时间
   - 数据库名称
   - 表总数

2. **目录**
   - 所有表的链接列表

3. **每个表的详细信息**
   - 表名和用途
   - 数据内容说明
   - 字段结构表格（字段名、类型、可空、默认值、说明）
   - 主键信息
   - 外键关系
   - 索引信息
   - 可用查询操作列表

4. **表关系总览**
   - 所有外键关系的汇总

### 输出示例

```markdown
## students

**用途**: 学生信息管理

**数据内容**: 学生基本信息（姓名、学号、入学日期等）

### 字段结构

| 字段名 | 类型 | 可空 | 默认值 | 说明 |
|--------|------|------|--------|------|
| student_id | TEXT | 否 | - | 唯一标识符 |
| name | TEXT | 否 | - | 名称 |
| email | TEXT | 是 | - | 电子邮件 |
| created_at | TIMESTAMP | 是 | CURRENT_TIMESTAMP | 创建时间 |

**主键**: student_id

### 外键关系

- `major_id` → `majors.major_id`

### 可用查询操作

- 查询所有students记录
- 根据ID查询单个students记录
- 根据name搜索students
- 根据email查找students
- 查询students及其关联的majors信息
- 统计students总数
- 按时间段统计students数量
```

### 高级用法

#### 在 Python 代码中使用

```python
from tools.db_schema_analyzer import DatabaseSchemaAnalyzer

# 创建分析器
analyzer = DatabaseSchemaAnalyzer("sqlite:///./data/config.db")

# 连接数据库
if analyzer.connect():
    # 生成文档
    content = analyzer.generate_markdown("output.md")
    
    # 或者只获取内容不写文件
    content = analyzer.generate_markdown()
    print(content)
    
    # 关闭连接
    analyzer.close()
```

#### 获取特定表信息

```python
from tools.db_schema_analyzer import DatabaseSchemaAnalyzer

analyzer = DatabaseSchemaAnalyzer("sqlite:///./data/config.db")
analyzer.connect()

# 获取所有表名
tables = analyzer.get_table_names()
print(f"数据库包含 {len(tables)} 个表")

# 获取特定表的信息
table_info = analyzer.get_table_info("students")
print(f"表名: {table_info['name']}")
print(f"字段数: {len(table_info['columns'])}")

analyzer.close()
```

### 注意事项

1. **数据库权限**: 确保提供的数据库用户有读取表结构的权限
2. **大型数据库**: 对于包含大量表的数据库，分析可能需要一些时间
3. **敏感信息**: 生成的文档不包含实际数据，只包含结构信息
4. **URL编码**: 如果密码包含特殊字符，需要进行URL编码

### 故障排除

#### 连接失败

```
✗ 数据库连接失败: (OperationalError) unable to open database file
```

**解决方案**: 检查数据库路径是否正确，文件是否存在

#### 驱动未安装

```
✗ 数据库连接失败: No module named 'psycopg2'
```

**解决方案**: 安装相应的数据库驱动
```bash
pip install psycopg2-binary
```

#### 权限不足

```
✗ 数据库连接失败: permission denied
```

**解决方案**: 确保数据库用户有足够的权限读取表结构

### 贡献

欢迎提交问题和改进建议！


---

## token_counter.py - Token计数工具 ⭐ NEW

### 功能说明

计算和比较不同schema表示方式的token数量，帮助优化LLM API成本。

**核心功能**:
- 使用tiktoken进行精确token计数
- 比较多个文件/数据库的token效率
- 逐行详细分析
- JSON导出用于自动化
- 支持多种编码方式（GPT-4, GPT-3等）

### 安装依赖

```bash
# 可选：安装tiktoken以获得精确计数
pip install tiktoken
```

不安装tiktoken时，工具会使用近似计数（仍可用于比较）。

### 使用方法

#### 基本比较

```bash
# 比较多个文件的token数量
python tools/token_counter.py data/test_medical.db data/schema_*.md

# 分析单个文件
python tools/token_counter.py data/schema_compact.md
```

#### 详细分析

```bash
# 显示逐行token分析
python tools/token_counter.py data/schema.md --detailed

# 显示token最多的前20行
python tools/token_counter.py data/schema.md --detailed --top 20
```

#### 导出结果

```bash
# 导出为JSON
python tools/token_counter.py data/*.md --output results.json

# 指定编码方式
python tools/token_counter.py file.md --encoding cl100k_base  # GPT-4
python tools/token_counter.py file.md --encoding p50k_base    # GPT-3
```

### 输出示例

```
====================================================================================================
TOKEN COUNT COMPARISON
====================================================================================================
Source                                        Chars      Words    Lines     Tokens   Efficiency
----------------------------------------------------------------------------------------------------
DB Schema: test_medical.db                   32,210      3,318    1,034      6,671       100.0%
test_medical_db_schema_description.md        12,862        978      603      7,221       108.2%
test_medical_db_schema_compact.md             6,956        656      158      1,609        24.1%
====================================================================================================

Token Reduction Summary:
  test_medical_db_schema_description.md: -8.2% vs baseline
  test_medical_db_schema_compact.md: +75.9% vs baseline
```

### 使用场景

- **优化API成本**: 精简版可节省75%+ token
- **比较不同表示方式**: 找出最高效的schema描述格式
- **识别token密集区域**: 找出需要优化的部分
- **成本估算**: 计算LLM API调用成本

---

## schema_compactor.py - Schema压缩工具 ⭐ NEW

### 功能说明

使用LLM自动生成精简的英文schema描述，大幅减少token消耗。

**核心功能**:
- 自动生成优化的schema描述
- 相比原始SQL减少75%+ token
- 保留关键关系和结构
- 可配置LLM后端

### 前置条件

1. 在`.env`中配置LLM服务：
```bash
LLM_API_URL=http://localhost:11434/v1/chat/completions
LLM_API_KEY=your_key_here
LLM_MODEL=qwen2.5:32b
```

2. 确保LLM服务正在运行（如Ollama）

### 使用方法

#### 基本用法

```bash
# 生成精简描述
python tools/schema_compactor.py data/test_medical.db -o data/schema_compact.md
```

#### 自定义LLM

```bash
# 使用自定义LLM端点
python tools/schema_compactor.py data/test_medical.db -o output.md \
  --api-url http://localhost:11434 \
  --model llama3:8b

# 指定API密钥
python tools/schema_compactor.py data/test_medical.db -o output.md \
  --api-key sk-xxxxx
```

### 工作流程

1. 从SQLite数据库提取schema
2. 分析表关系（外键）
3. 发送优化提示词到LLM
4. 生成精简英文描述
5. 保存为markdown文件

### 生成的内容

生成的文件包含：
- 按业务领域分组的表
- 使用箭头(→)表示的关系
- 主键/外键标注（PK:, FK:）
- 重要约束
- 常见查询模式
- 设计特点

### 优势

- **降低API成本**: 节省75%+ token
- **提高准确性**: LLM更容易理解业务逻辑
- **更好的上下文**: 保留关键信息，去除冗余

---

## 完整工作流示例

### 步骤1: 分析当前状态

```bash
# 检查现有表示方式的token数量
python tools/token_counter.py \
  data/test_medical.db \
  data/existing_schema.md
```

### 步骤2: 生成精简版本

```bash
# 生成优化描述
python tools/schema_compactor.py \
  data/test_medical.db \
  -o data/schema_compact.md
```

### 步骤3: 比较结果

```bash
# 比较所有版本
python tools/token_counter.py \
  data/test_medical.db \
  data/existing_schema.md \
  data/schema_compact.md \
  --detailed
```

### 步骤4: 在生产环境使用

```python
# 在应用中使用
with open('data/schema_compact.md', 'r') as f:
    schema_context = f.read()

# 发送给LLM
prompt = f"""Database Schema:
{schema_context}

User Query: {user_question}

Generate SQL:"""
```

---

## Token优化技巧

### 最佳实践

1. **使用英文**: 比中文节省60-70% token
2. **去除冗余**: 消除冗长的解释
3. **使用符号**: → 表示关系，PK:/FK: 表示键
4. **逻辑分组**: 按业务领域而非字母顺序
5. **关注结构**: 关系优先于字段描述
6. **明智缩写**: 常用术语（ID, FK, PK等）

### Token减少策略

| 策略 | Token减少 | 权衡 |
|------|----------|------|
| 英文 vs 中文 | 60-70% | 无（如果LLM支持英文）|
| 精简格式 | 40-50% | 可读性略降 |
| 移除示例 | 20-30% | LLM上下文减少 |
| 使用缩写 | 10-20% | 必须清晰 |
| 移除注释 | 10-15% | 解释减少 |

### API成本对比

假设GPT-4定价（$0.03/1K输入token）：

| 格式 | Token数 | 每次查询成本 | 1000次查询成本 |
|------|---------|-------------|---------------|
| 原始Schema | 6,671 | $0.20 | $200 |
| 详细MD | 7,221 | $0.22 | $217 |
| 精简MD | 1,609 | $0.05 | $48 |

**使用精简格式节省: 76% API成本**

---

## 测试工具

运行测试套件验证所有工具：

```bash
bash tools/test_schema_tools.sh
```

---

## 更多文档

详细文档请参阅：
- [SCHEMA_TOOLS.md](./SCHEMA_TOOLS.md) - 完整使用指南
- [使用说明.md](./使用说明.md) - 中文详细说明
- [example_usage.py](./example_usage.py) - Python示例代码
- [example_usage.sh](./example_usage.sh) - Shell脚本示例
