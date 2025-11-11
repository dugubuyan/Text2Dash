"""
数据源管理器测试
"""
import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.services.data_source_manager import DataSourceManager, CombinedData
from backend.services.database_connector import DatabaseConnector, QueryResult
from backend.services.mcp_connector import MCPConnector, MCPResult
from backend.services.dto import QueryPlan, SQLQuery, MCPCall, DataMetadata


async def test_basic_initialization():
    """测试基础初始化"""
    print("\n=== 测试1: 基础初始化 ===")
    
    manager = DataSourceManager()
    print(f"✓ 数据源管理器初始化成功")
    print(f"  临时数据库路径: {manager.temp_db_path}")
    print(f"  数据库连接器: {type(manager.db).__name__}")
    print(f"  MCP连接器: {type(manager.mcp).__name__}")
    
    # 测试自定义临时数据库路径
    custom_path = "data/custom_temp.db"
    manager2 = DataSourceManager(temp_db_path=custom_path)
    assert manager2.temp_db_path == custom_path
    print(f"✓ 自定义临时数据库路径: {manager2.temp_db_path}")


async def test_temp_table_creation():
    """测试临时表创建"""
    print("\n=== 测试2: 临时表创建 ===")
    
    manager = DataSourceManager(temp_db_path="data/test_temp.db")
    
    # 模拟数据库查询结果
    db_result = QueryResult(
        data=[
            {"id": 1, "name": "Alice", "age": 30},
            {"id": 2, "name": "Bob", "age": 25},
            {"id": 3, "name": "Charlie", "age": 35}
        ],
        columns=["id", "name", "age"]
    )
    
    # 模拟MCP结果
    mcp_result = MCPResult(
        tool_name="get_sales",
        data=[
            {"product": "A", "sales": 100},
            {"product": "B", "sales": 200}
        ],
        metadata=DataMetadata(
            columns=["product", "sales"],
            column_types={"product": "TEXT", "sales": "INTEGER"},
            row_count=2
        )
    )
    
    # 创建查询计划
    sql_queries = [
        SQLQuery(db_config_id="db1", sql="SELECT * FROM users", source_alias="users")
    ]
    mcp_calls = [
        MCPCall(
            mcp_config_id="mcp1",
            tool_name="get_sales",
            parameters={},
            source_alias="sales"
        )
    ]
    
    # 创建临时表
    table_mapping = await manager.create_temp_tables(
        mcp_results=[mcp_result],
        db_results=[db_result],
        sql_queries=sql_queries,
        mcp_calls=mcp_calls
    )
    
    print(f"✓ 临时表创建成功")
    print(f"  表映射: {table_mapping}")
    
    # 验证临时数据库文件存在
    assert os.path.exists(manager.temp_db_path)
    print(f"✓ 临时数据库文件存在: {manager.temp_db_path}")
    
    # 清理
    manager.cleanup_temp_tables()
    assert not os.path.exists(manager.temp_db_path)
    print(f"✓ 临时数据库清理成功")


async def test_combine_data_with_sql():
    """测试SQL数据组合"""
    print("\n=== 测试3: SQL数据组合 ===")
    
    manager = DataSourceManager(temp_db_path="data/test_combine.db")
    
    # 创建测试数据
    db_result = QueryResult(
        data=[
            {"user_id": 1, "name": "Alice"},
            {"user_id": 2, "name": "Bob"}
        ],
        columns=["user_id", "name"]
    )
    
    mcp_result = MCPResult(
        tool_name="get_orders",
        data=[
            {"user_id": 1, "order_count": 5},
            {"user_id": 2, "order_count": 3}
        ],
        metadata=DataMetadata(
            columns=["user_id", "order_count"],
            column_types={"user_id": "INTEGER", "order_count": "INTEGER"},
            row_count=2
        )
    )
    
    sql_queries = [
        SQLQuery(db_config_id="db1", sql="SELECT * FROM users", source_alias="users")
    ]
    mcp_calls = [
        MCPCall(
            mcp_config_id="mcp1",
            tool_name="get_orders",
            parameters={},
            source_alias="orders"
        )
    ]
    
    # 创建临时表
    await manager.create_temp_tables(
        mcp_results=[mcp_result],
        db_results=[db_result],
        sql_queries=sql_queries,
        mcp_calls=mcp_calls
    )
    
    # 执行组合SQL
    combination_sql = """
        SELECT u.user_id, u.name, o.order_count
        FROM temp_users u
        JOIN temp_orders o ON u.user_id = o.user_id
    """
    
    combined_data = await manager.combine_data_with_sql(combination_sql)
    
    print(f"✓ SQL组合执行成功")
    print(f"  结果行数: {len(combined_data.data)}")
    print(f"  列名: {combined_data.columns}")
    print(f"  数据: {combined_data.data}")
    
    assert len(combined_data.data) == 2
    assert "name" in combined_data.columns
    assert "order_count" in combined_data.columns
    
    # 清理
    manager.cleanup_temp_tables()
    print(f"✓ 测试完成并清理")


async def test_get_combined_metadata():
    """测试组合数据元信息提取"""
    print("\n=== 测试4: 组合数据元信息提取 ===")
    
    manager = DataSourceManager()
    
    # 创建测试数据
    combined_data = CombinedData(
        data=[
            {"id": 1, "name": "Alice", "score": 95.5, "active": True},
            {"id": 2, "name": "Bob", "score": 87.3, "active": False}
        ],
        columns=["id", "name", "score", "active"]
    )
    
    # 提取元信息
    metadata = manager.get_combined_metadata(combined_data)
    
    print(f"✓ 元信息提取成功")
    print(f"  列名: {metadata.columns}")
    print(f"  列类型: {metadata.column_types}")
    print(f"  行数: {metadata.row_count}")
    
    assert metadata.row_count == 2
    assert len(metadata.columns) == 4
    assert metadata.column_types["id"] == "INTEGER"
    assert metadata.column_types["name"] == "TEXT"
    assert metadata.column_types["score"] == "FLOAT"
    assert metadata.column_types["active"] == "BOOLEAN"
    
    print(f"✓ 所有断言通过")


async def test_empty_data_handling():
    """测试空数据处理"""
    print("\n=== 测试5: 空数据处理 ===")
    
    manager = DataSourceManager()
    
    # 测试空数据的元信息提取
    empty_data = CombinedData(data=[], columns=["col1", "col2"])
    metadata = manager.get_combined_metadata(empty_data)
    
    print(f"✓ 空数据元信息提取成功")
    print(f"  行数: {metadata.row_count}")
    print(f"  列类型: {metadata.column_types}")
    
    assert metadata.row_count == 0
    assert all(t == "UNKNOWN" for t in metadata.column_types.values())
    
    print(f"✓ 空数据处理正确")


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("数据源管理器测试套件")
    print("=" * 60)
    
    try:
        await test_basic_initialization()
        await test_temp_table_creation()
        await test_combine_data_with_sql()
        await test_get_combined_metadata()
        await test_empty_data_handling()
        
        print("\n" + "=" * 60)
        print("✓ 所有测试通过!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
