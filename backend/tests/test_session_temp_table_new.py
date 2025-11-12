"""
测试新的 session 临时表查询逻辑
验证通过 db_config_id="__session__" 来查询临时表
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.services.llm_service import LLMService
from backend.services.dto import ConversationMessage


async def test_temp_table_query():
    """测试临时表查询功能"""
    print("\n" + "="*60)
    print("测试新的临时表查询逻辑")
    print("="*60)
    
    # 初始化 LLM 服务
    llm = LLMService()
    
    # 模拟 session 临时表
    session_temp_tables = [
        {
            "table_name": "temp_session_abc123_interaction_1",
            "user_query": "查询所有学生信息",
            "row_count": 100,
            "columns": [
                {"name": "student_id", "type": "INTEGER"},
                {"name": "name", "type": "TEXT"},
                {"name": "age", "type": "INTEGER"},
                {"name": "grade", "type": "TEXT"}
            ]
        }
    ]
    
    # 测试1: 查询前10条记录
    print("\n测试1: 查询前10条记录")
    print("-" * 60)
    query_plan = await llm.generate_query_plan(
        query="显示前10条记录",
        db_schemas={},
        mcp_tools={},
        context=[],
        session_temp_tables=session_temp_tables
    )
    
    print(f"✓ no_data_source_match: {query_plan.no_data_source_match}")
    print(f"✓ SQL查询数量: {len(query_plan.sql_queries)}")
    
    if query_plan.sql_queries:
        sql_query = query_plan.sql_queries[0]
        print(f"✓ db_config_id: {sql_query.db_config_id}")
        print(f"✓ SQL: {sql_query.sql}")
        
        # 验证是否使用了 __session__
        assert sql_query.db_config_id == "__session__", "应该使用 __session__ 作为 db_config_id"
        assert "temp_session_abc123_interaction_1" in sql_query.sql, "SQL 应该包含临时表名"
        assert "LIMIT 10" in sql_query.sql.upper(), "SQL 应该包含 LIMIT 10"
        print("✅ 测试1通过")
    else:
        print("❌ 测试1失败: 没有生成 SQL 查询")
    
    # 测试2: 按年龄排序
    print("\n测试2: 按年龄排序")
    print("-" * 60)
    query_plan = await llm.generate_query_plan(
        query="按年龄从大到小排序",
        db_schemas={},
        mcp_tools={},
        context=[],
        session_temp_tables=session_temp_tables
    )
    
    print(f"✓ SQL查询数量: {len(query_plan.sql_queries)}")
    
    if query_plan.sql_queries:
        sql_query = query_plan.sql_queries[0]
        print(f"✓ db_config_id: {sql_query.db_config_id}")
        print(f"✓ SQL: {sql_query.sql}")
        
        # 验证
        assert sql_query.db_config_id == "__session__", "应该使用 __session__"
        assert "ORDER BY" in sql_query.sql.upper(), "SQL 应该包含 ORDER BY"
        assert "age" in sql_query.sql.lower(), "SQL 应该包含 age 字段"
        print("✅ 测试2通过")
    else:
        print("❌ 测试2失败: 没有生成 SQL 查询")
    
    # 测试3: 筛选条件
    print("\n测试3: 筛选年龄大于18的学生")
    print("-" * 60)
    query_plan = await llm.generate_query_plan(
        query="筛选年龄大于18的学生",
        db_schemas={},
        mcp_tools={},
        context=[],
        session_temp_tables=session_temp_tables
    )
    
    print(f"✓ SQL查询数量: {len(query_plan.sql_queries)}")
    
    if query_plan.sql_queries:
        sql_query = query_plan.sql_queries[0]
        print(f"✓ db_config_id: {sql_query.db_config_id}")
        print(f"✓ SQL: {sql_query.sql}")
        
        # 验证
        assert sql_query.db_config_id == "__session__", "应该使用 __session__"
        assert "WHERE" in sql_query.sql.upper(), "SQL 应该包含 WHERE"
        assert "age" in sql_query.sql.lower(), "SQL 应该包含 age 字段"
        print("✅ 测试3通过")
    else:
        print("❌ 测试3失败: 没有生成 SQL 查询")
    
    print("\n" + "="*60)
    print("所有测试完成！")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_temp_table_query())
