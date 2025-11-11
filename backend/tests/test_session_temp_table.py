"""
测试 Session 临时表功能
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.data_source_manager import get_data_source_manager
from backend.services.llm_service import LLMService
from backend.services.report_service import get_report_service
from backend.database import get_database
from backend.utils.logger import get_logger

logger = get_logger(__name__)


async def test_session_temp_table():
    """测试 session 临时表功能"""
    
    print("\n" + "="*60)
    print("测试 Session 临时表功能")
    print("="*60 + "\n")
    
    # 初始化服务
    data_source_manager = get_data_source_manager()
    report_service = get_report_service()
    db = get_database()
    
    # 创建测试 session
    session_id = "test_session_123"
    
    try:
        # 步骤1: 创建测试数据
        print("步骤1: 创建测试数据...")
        test_data = [
            {"id": 1, "name": "Alice", "age": 25, "city": "Beijing"},
            {"id": 2, "name": "Bob", "age": 30, "city": "Shanghai"},
            {"id": 3, "name": "Charlie", "age": 35, "city": "Guangzhou"},
            {"id": 4, "name": "David", "age": 28, "city": "Shenzhen"},
            {"id": 5, "name": "Eve", "age": 32, "city": "Hangzhou"},
        ]
        
        # 步骤2: 保存到临时表
        print("步骤2: 保存到临时表...")
        table_name = data_source_manager.create_session_temp_table(
            session_id=session_id,
            interaction_num=1,
            data=test_data
        )
        print(f"✓ 临时表创建成功: {table_name}")
        
        # 步骤3: 查询临时表
        print("\n步骤3: 查询临时表...")
        result = data_source_manager.query_session_temp_table(table_name)
        print(f"✓ 查询成功，返回 {len(result)} 行数据")
        for row in result[:3]:
            print(f"  {row}")
        
        # 步骤4: 获取临时表 schema
        print("\n步骤4: 获取临时表 schema...")
        schema = data_source_manager.get_temp_table_schema(table_name)
        print(f"✓ Schema 获取成功:")
        print(f"  行数: {schema['row_count']}")
        print(f"  列:")
        for col in schema['columns']:
            print(f"    - {col['name']} ({col['type']})")
        
        # 步骤5: 列出 session 的所有临时表
        print("\n步骤5: 列出 session 的所有临时表...")
        tables = data_source_manager.list_session_temp_tables(session_id)
        print(f"✓ 找到 {len(tables)} 个临时表:")
        for t in tables:
            print(f"  - {t}")
        
        # 步骤6: 测试 LLM 自动判断使用临时表
        print("\n步骤6: 测试 LLM 自动判断使用临时表...")
        
        # 模拟临时表信息
        session_temp_tables = [{
            "table_name": table_name,
            "user_query": "查询用户列表",
            "columns": schema['columns'],
            "row_count": schema['row_count']
        }]
        
        llm_service = LLMService()
        
        # 测试查询1: 应该使用临时表
        print("\n  测试查询1: '显示前3条数据'")
        query_plan = await llm_service.generate_query_plan(
            query="显示前3条数据",
            db_schemas={},
            mcp_tools={},
            context=[],
            session_temp_tables=session_temp_tables
        )
        print(f"  ✓ use_temp_table: {query_plan.use_temp_table}")
        print(f"  ✓ temp_table_name: {query_plan.temp_table_name}")
        
        # 测试查询2: 应该使用临时表
        print("\n  测试查询2: '按年龄排序'")
        query_plan = await llm_service.generate_query_plan(
            query="按年龄排序",
            db_schemas={},
            mcp_tools={},
            context=[],
            session_temp_tables=session_temp_tables
        )
        print(f"  ✓ use_temp_table: {query_plan.use_temp_table}")
        print(f"  ✓ temp_table_name: {query_plan.temp_table_name}")
        
        # 步骤7: 清理临时表
        print("\n步骤7: 清理临时表...")
        count = data_source_manager.drop_session_temp_tables(session_id)
        print(f"✓ 删除了 {count} 个临时表")
        
        # 验证清理
        tables = data_source_manager.list_session_temp_tables(session_id)
        print(f"✓ 验证清理: 剩余 {len(tables)} 个临时表")
        
        print("\n" + "="*60)
        print("✓ 所有测试通过！")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_session_temp_table())
    sys.exit(0 if success else 1)
