"""
测试MCP修复：验证当没有配置MCP时，LLM不会返回MCP调用
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from backend.services.llm_service import LLMService


async def test_no_mcp_configured():
    """测试没有配置MCP时的行为"""
    llm = LLMService()
    
    # 模拟只有数据库，没有MCP的情况
    db_schemas = {
        "test-db-id": {
            "name": "测试数据库",
            "type": "sqlite",
            "tables": {
                "students": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "age", "type": "INTEGER"}
                ],
                "majors": [
                    {"name": "major_id", "type": "INTEGER"},
                    {"name": "major_name", "type": "TEXT"}
                ]
            }
        }
    }
    
    # 空的MCP工具字典（模拟没有配置MCP的情况）
    mcp_tools = {}
    
    # 测试查询
    query = "查询所有学生的姓名和年龄"
    
    print("=" * 60)
    print("测试场景：没有配置MCP服务器")
    print("=" * 60)
    print(f"查询: {query}")
    print(f"数据库: {list(db_schemas.keys())}")
    print(f"MCP工具: {mcp_tools}")
    print()
    
    try:
        query_plan = await llm.generate_query_plan(
            query=query,
            db_schemas=db_schemas,
            mcp_tools=mcp_tools,
            model="gemini/gemini-2.0-flash-exp"
        )
        
        print("查询计划生成成功！")
        print(f"SQL查询数量: {len(query_plan.sql_queries)}")
        print(f"MCP调用数量: {len(query_plan.mcp_calls)}")
        print()
        
        if query_plan.mcp_calls:
            print("❌ 测试失败：LLM返回了MCP调用，但没有配置MCP服务器！")
            print("MCP调用详情:")
            for mcp_call in query_plan.mcp_calls:
                print(f"  - {mcp_call.mcp_config_id}: {mcp_call.tool_name}")
            return False
        else:
            print("✅ 测试通过：LLM没有返回MCP调用")
            
        if query_plan.sql_queries:
            print(f"✅ SQL查询正常生成 ({len(query_plan.sql_queries)}条)")
            for i, sql_query in enumerate(query_plan.sql_queries, 1):
                print(f"\nSQL {i}:")
                print(f"  数据库ID: {sql_query.db_config_id}")
                print(f"  别名: {sql_query.source_alias}")
                print(f"  SQL: {sql_query.sql}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """运行测试"""
    print("\n开始测试MCP修复...\n")
    
    success = await test_no_mcp_configured()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 所有测试通过！")
    else:
        print("❌ 测试失败！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
