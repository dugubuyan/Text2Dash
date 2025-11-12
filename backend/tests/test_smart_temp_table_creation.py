"""
测试智能临时表创建逻辑
验证只在必要时创建临时表
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.services.dto import QueryPlan, SQLQuery, MCPCall
from backend.services.report_service import ReportService


def test_should_create_temp_table():
    """测试临时表创建判断逻辑"""
    
    # 创建 ReportService 实例（只用于测试方法，传入 None 作为依赖）
    service = ReportService(
        llm_service=None,
        data_source_manager=None,
        filter_service=None,
        session_manager=None,
        database=None
    )
    
    print("\n" + "="*60)
    print("测试智能临时表创建逻辑")
    print("="*60)
    
    # 测试1：查询原始数据源 → 应该创建
    print("\n测试1: 查询原始数据源")
    query_plan = QueryPlan(
        sql_queries=[
            SQLQuery(db_config_id="mysql_db_1", sql="SELECT * FROM users", source_alias="users")
        ]
    )
    result = service._should_create_temp_table(query_plan)
    print(f"  查询计划: 查询 mysql_db_1")
    print(f"  结果: {'✅ 需要创建' if result else '❌ 不需要创建'}")
    assert result == True, "查询原始数据源应该创建临时表"
    
    # 测试2：只查询临时表 → 不应该创建
    print("\n测试2: 只查询临时表（简单子集）")
    query_plan = QueryPlan(
        sql_queries=[
            SQLQuery(
                db_config_id="__session__",
                sql="SELECT * FROM session_abc_interaction_1 LIMIT 10",
                source_alias="result"
            )
        ]
    )
    result = service._should_create_temp_table(query_plan)
    print(f"  查询计划: 查询临时表 LIMIT 10")
    print(f"  结果: {'✅ 需要创建' if result else '❌ 不需要创建'}")
    assert result == False, "简单临时表查询不应该创建临时表"
    
    # 测试3：有 MCP 调用 → 应该创建
    print("\n测试3: 有 MCP 调用")
    query_plan = QueryPlan(
        mcp_calls=[
            MCPCall(
                mcp_config_id="mcp_1",
                tool_name="get_weather",
                parameters={},
                source_alias="weather"
            )
        ]
    )
    result = service._should_create_temp_table(query_plan)
    print(f"  查询计划: MCP 调用")
    print(f"  结果: {'✅ 需要创建' if result else '❌ 不需要创建'}")
    assert result == True, "有 MCP 调用应该创建临时表"
    
    # 测试4：需要数据组合 → 应该创建
    print("\n测试4: 需要数据组合")
    query_plan = QueryPlan(
        sql_queries=[
            SQLQuery(db_config_id="__session__", sql="SELECT * FROM temp1", source_alias="t1"),
            SQLQuery(db_config_id="__session__", sql="SELECT * FROM temp2", source_alias="t2")
        ],
        needs_combination=True
    )
    result = service._should_create_temp_table(query_plan)
    print(f"  查询计划: 需要数据组合")
    print(f"  结果: {'✅ 需要创建' if result else '❌ 不需要创建'}")
    assert result == True, "需要数据组合应该创建临时表"
    
    # 测试5：混合查询（临时表 + 原始数据库）→ 应该创建
    print("\n测试5: 混合查询（临时表 + 原始数据库）")
    query_plan = QueryPlan(
        sql_queries=[
            SQLQuery(db_config_id="__session__", sql="SELECT * FROM temp1", source_alias="t1"),
            SQLQuery(db_config_id="mysql_db_1", sql="SELECT * FROM orders", source_alias="orders")
        ],
        needs_combination=True
    )
    result = service._should_create_temp_table(query_plan)
    print(f"  查询计划: 临时表 + 原始数据库")
    print(f"  结果: {'✅ 需要创建' if result else '❌ 不需要创建'}")
    assert result == True, "混合查询应该创建临时表"
    
    # 测试6：临时表排序查询 → 不应该创建
    print("\n测试6: 临时表排序查询")
    query_plan = QueryPlan(
        sql_queries=[
            SQLQuery(
                db_config_id="__session__",
                sql="SELECT * FROM session_abc_interaction_1 ORDER BY age DESC",
                source_alias="result"
            )
        ]
    )
    result = service._should_create_temp_table(query_plan)
    print(f"  查询计划: 临时表排序")
    print(f"  结果: {'✅ 需要创建' if result else '❌ 不需要创建'}")
    assert result == False, "临时表排序查询不应该创建临时表"
    
    print("\n" + "="*60)
    print("✅ 所有测试通过！")
    print("="*60)


if __name__ == "__main__":
    test_should_create_temp_table()
