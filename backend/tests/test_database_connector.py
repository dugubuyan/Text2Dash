"""
测试数据库连接器
"""
import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.database import init_database, get_database
from backend.models.database_config import DatabaseConfig
from backend.services.database_connector import get_database_connector
from backend.services.encryption_service import get_encryption_service


async def test_database_connector():
    """测试数据库连接器功能"""
    print("=" * 60)
    print("测试数据库连接器")
    print("=" * 60)
    
    # 初始化配置数据库
    print("\n1. 初始化配置数据库...")
    init_database()
    
    # 获取服务实例
    db = get_database()
    connector = get_database_connector()
    encryption_service = get_encryption_service()
    
    # 创建测试数据库配置
    print("\n2. 创建测试数据库配置...")
    test_db_path = "./data/test_medical.db"
    
    # 确保测试数据库存在
    os.makedirs(os.path.dirname(test_db_path), exist_ok=True)
    
    # 创建一个简单的测试数据库
    import sqlite3
    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()
    
    # 创建测试表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER,
            grade REAL
        )
    """)
    
    # 插入测试数据
    cursor.execute("DELETE FROM students")  # 清空旧数据
    test_data = [
        (1, "张三", 20, 85.5),
        (2, "李四", 21, 90.0),
        (3, "王五", 19, 78.5),
    ]
    cursor.executemany(
        "INSERT INTO students (id, name, age, grade) VALUES (?, ?, ?, ?)",
        test_data
    )
    conn.commit()
    conn.close()
    
    print(f"   创建测试数据库: {test_db_path}")
    print(f"   插入 {len(test_data)} 条测试数据")
    
    # 保存数据库配置到配置数据库
    with db.get_session() as session:
        # 删除旧配置
        session.query(DatabaseConfig).filter_by(name="测试数据库").delete()
        
        db_config = DatabaseConfig(
            id="test-db-001",
            name="测试数据库",
            type="sqlite",
            url=f"sqlite:///{test_db_path}",
            username=None,
            encrypted_password=None
        )
        session.add(db_config)
        session.commit()
        print(f"   保存配置: {db_config.name} (ID: {db_config.id})")
    
    # 测试连接
    print("\n3. 测试数据库连接...")
    with db.get_session() as session:
        db_config = session.query(DatabaseConfig).filter_by(id="test-db-001").first()
        result = await connector.test_connection(db_config)
        print(f"   连接测试: {'成功' if result.success else '失败'}")
        print(f"   消息: {result.message}")
        if result.error:
            print(f"   错误: {result.error}")
    
    # 测试获取Schema信息
    print("\n4. 测试获取Schema信息...")
    schema_info = await connector.get_schema_info("test-db-001")
    print(f"   表数量: {len(schema_info.tables)}")
    for table_name, columns in schema_info.tables.items():
        print(f"   表: {table_name}")
        for col in columns:
            print(f"      - {col['name']}: {col['type']}")
    
    # 测试执行查询
    print("\n5. 测试执行SQL查询...")
    sql = "SELECT * FROM students WHERE age >= 20"
    query_result = await connector.execute_query("test-db-001", sql)
    print(f"   SQL: {sql}")
    print(f"   结果行数: {len(query_result.data)}")
    print(f"   列名: {query_result.columns}")
    print(f"   数据:")
    for row in query_result.data:
        print(f"      {row}")
    
    # 测试提取数据元信息
    print("\n6. 测试提取数据元信息...")
    metadata = connector.get_data_metadata(query_result)
    print(f"   列名: {metadata.columns}")
    print(f"   列类型: {metadata.column_types}")
    print(f"   行数: {metadata.row_count}")
    
    # 测试聚合查询
    print("\n7. 测试聚合查询...")
    sql = "SELECT COUNT(*) as total, AVG(grade) as avg_grade FROM students"
    query_result = await connector.execute_query("test-db-001", sql)
    print(f"   SQL: {sql}")
    print(f"   结果: {query_result.data}")
    metadata = connector.get_data_metadata(query_result)
    print(f"   元信息: columns={metadata.columns}, types={metadata.column_types}")
    
    # 清理
    print("\n8. 清理连接...")
    connector.close_all_connections()
    print("   所有连接已关闭")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_database_connector())
