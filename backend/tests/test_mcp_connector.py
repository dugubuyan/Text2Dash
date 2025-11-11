"""
MCP连接器测试
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.services.mcp_connector import MCPConnector


async def test_validate_tool_response():
    """测试数据格式验证"""
    print("\n=== 测试MCP数据格式验证 ===")
    
    connector = MCPConnector()
    
    # 测试1: 有效的表格数据
    valid_data = [
        {"id": 1, "name": "Alice", "age": 30},
        {"id": 2, "name": "Bob", "age": 25},
        {"id": 3, "name": "Charlie", "age": 35}
    ]
    result = connector.validate_tool_response(valid_data)
    print(f"✓ 有效表格数据验证: {result}")
    assert result == True, "应该验证通过"
    
    # 测试2: 空列表（有效）
    empty_data = []
    result = connector.validate_tool_response(empty_data)
    print(f"✓ 空列表验证: {result}")
    assert result == True, "空列表应该验证通过"
    
    # 测试3: 非列表数据（无效）
    invalid_data1 = {"id": 1, "name": "Alice"}
    result = connector.validate_tool_response(invalid_data1)
    print(f"✓ 非列表数据验证: {result}")
    assert result == False, "非列表应该验证失败"
    
    # 测试4: 列表元素不是字典（无效）
    invalid_data2 = [1, 2, 3]
    result = connector.validate_tool_response(invalid_data2)
    print(f"✓ 列表元素非字典验证: {result}")
    assert result == False, "列表元素非字典应该验证失败"
    
    # 测试5: 字典键不一致（无效）
    invalid_data3 = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "age": 25}  # 缺少name，多了age
    ]
    result = connector.validate_tool_response(invalid_data3)
    print(f"✓ 字典键不一致验证: {result}")
    assert result == False, "字典键不一致应该验证失败"
    
    print("\n所有数据格式验证测试通过！")


async def test_get_tool_metadata():
    """测试元信息提取"""
    print("\n=== 测试MCP数据元信息提取 ===")
    
    connector = MCPConnector()
    
    # 测试1: 正常数据
    data = [
        {"id": 1, "name": "Alice", "age": 30, "active": True, "score": 95.5},
        {"id": 2, "name": "Bob", "age": 25, "active": False, "score": 87.3},
        {"id": 3, "name": "Charlie", "age": 35, "active": True, "score": 92.1}
    ]
    metadata = connector.get_tool_metadata(data)
    
    print(f"列名: {metadata.columns}")
    print(f"列类型: {metadata.column_types}")
    print(f"行数: {metadata.row_count}")
    
    assert metadata.row_count == 3, "行数应该是3"
    assert len(metadata.columns) == 5, "应该有5列"
    assert "id" in metadata.columns, "应该包含id列"
    assert metadata.column_types["id"] == "INTEGER", "id应该是INTEGER类型"
    assert metadata.column_types["name"] == "TEXT", "name应该是TEXT类型"
    assert metadata.column_types["age"] == "INTEGER", "age应该是INTEGER类型"
    assert metadata.column_types["active"] == "BOOLEAN", "active应该是BOOLEAN类型"
    assert metadata.column_types["score"] == "FLOAT", "score应该是FLOAT类型"
    
    print("✓ 正常数据元信息提取测试通过")
    
    # 测试2: 空数据
    empty_data = []
    metadata = connector.get_tool_metadata(empty_data)
    
    print(f"\n空数据 - 列名: {metadata.columns}")
    print(f"空数据 - 行数: {metadata.row_count}")
    
    assert metadata.row_count == 0, "行数应该是0"
    assert len(metadata.columns) == 0, "应该没有列"
    
    print("✓ 空数据元信息提取测试通过")
    
    # 测试3: 包含NULL值的数据
    data_with_null = [
        {"id": 1, "name": None, "age": 30},
        {"id": 2, "name": "Bob", "age": None},
        {"id": 3, "name": "Charlie", "age": 35}
    ]
    metadata = connector.get_tool_metadata(data_with_null)
    
    print(f"\n包含NULL值 - 列类型: {metadata.column_types}")
    
    # name列第一行是None，但第二行是字符串，应该推断为TEXT
    assert metadata.column_types["name"] == "TEXT", "name应该推断为TEXT类型"
    # age列第一行有值，应该推断为INTEGER
    assert metadata.column_types["age"] == "INTEGER", "age应该推断为INTEGER类型"
    
    print("✓ 包含NULL值数据元信息提取测试通过")
    
    print("\n所有元信息提取测试通过！")


async def main():
    """运行所有测试"""
    print("开始测试MCP连接器...")
    
    try:
        await test_validate_tool_response()
        await test_get_tool_metadata()
        
        print("\n" + "="*50)
        print("所有测试通过！✓")
        print("="*50)
    
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
