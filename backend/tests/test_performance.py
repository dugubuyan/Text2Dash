"""
性能测试脚本 - 分析报表生成各阶段耗时
"""
import asyncio
import time
import json
from datetime import datetime

from backend.services.llm_service import LLMService
from backend.services.data_source_manager import DataSourceManager
from backend.services.session_manager import SessionManager
from backend.database import get_database


async def test_session_save_performance():
    """测试会话保存性能"""
    print("\n=== 测试会话保存性能 ===\n")
    
    db = get_database()
    session_manager = SessionManager(db)
    
    # 创建测试会话
    session_id = await session_manager.create_session(user_id="test_user")
    print(f"创建测试会话: {session_id}")
    
    # 模拟报表数据
    test_data = [{"col1": f"value{i}", "col2": i} for i in range(100)]
    chart_config = {
        "title": {"text": "测试图表"},
        "xAxis": {"type": "category"},
        "yAxis": {"type": "value"},
        "series": [{"type": "bar", "data": [1, 2, 3]}]
    }
    
    # 测试不同数据量的保存时间
    for snapshot_size in [0, 10, 50, 100]:
        start = time.time()
        
        interaction_id = await session_manager.add_interaction(
            session_id=session_id,
            user_query="测试查询",
            sql_query="SELECT * FROM test",
            chart_config=chart_config,
            summary="测试总结",
            data_snapshot=test_data[:snapshot_size]
        )
        
        elapsed = time.time() - start
        print(f"保存 {snapshot_size} 行数据快照: {elapsed:.2f}秒")
    
    print("\n建议：如果保存时间 > 1秒，考虑减少快照大小或异步保存")


async def test_llm_performance():
    """测试LLM调用性能"""
    print("\n=== 测试LLM调用性能 ===\n")
    
    llm = LLMService()
    
    # 测试1: 简单查询计划生成
    start = time.time()
    
    db_schemas = {
        "test-db": {
            "name": "测试数据库",
            "type": "sqlite",
            "tables": {
                "students": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "score", "type": "REAL"}
                ]
            }
        }
    }
    
    query_plan = await llm.generate_query_plan(
        query="查询所有学生的平均分数",
        db_schemas=db_schemas,
        mcp_tools={},
        context=[],
        model="gemini/gemini-2.0-flash"
    )
    
    elapsed = time.time() - start
    print(f"生成查询计划: {elapsed:.2f}秒")
    
    # 测试2: 图表分析
    start = time.time()
    
    from backend.services.dto import DataMetadata
    
    metadata = DataMetadata(
        columns=["name", "avg_score"],
        column_types={"name": "TEXT", "avg_score": "REAL"},
        row_count=10
    )
    
    chart_suggestion = await llm.analyze_data_and_suggest_chart(
        query="查询所有学生的平均分数",
        metadata=metadata,
        model="gemini/gemini-2.0-flash"
    )
    
    elapsed = time.time() - start
    print(f"生成图表配置: {elapsed:.2f}秒")
    
    print("\n说明：LLM调用时间主要取决于网络和API响应，优化空间有限")


async def test_database_query_performance():
    """测试数据库查询性能"""
    print("\n=== 测试数据库查询性能 ===\n")
    
    from backend.services.database_connector import get_database_connector
    
    db_connector = get_database_connector()
    
    # 测试简单查询
    start = time.time()
    result = await db_connector.execute_query(
        db_config_id="test-db-001",
        sql="SELECT * FROM students LIMIT 100"
    )
    elapsed = time.time() - start
    print(f"简单查询 (100行): {elapsed:.4f}秒")
    
    # 测试复杂JOIN查询
    start = time.time()
    result = await db_connector.execute_query(
        db_config_id="test-db-001",
        sql="""
        SELECT s.name, AVG(e.grade_points) as avg_score
        FROM students s
        LEFT JOIN student_enrollments e ON s.student_id = e.student_id
        GROUP BY s.student_id
        ORDER BY avg_score DESC
        LIMIT 10
        """
    )
    elapsed = time.time() - start
    print(f"复杂JOIN查询: {elapsed:.4f}秒")
    
    print("\n说明：对于小数据量(<10000行)，SQL优化效果有限")
    print("建议：只有在查询时间 > 1秒时才考虑添加索引")


async def main():
    """运行所有性能测试"""
    print("=" * 60)
    print("报表生成性能分析")
    print("=" * 60)
    
    try:
        await test_session_save_performance()
        await test_llm_performance()
        await test_database_query_performance()
        
        print("\n" + "=" * 60)
        print("性能优化建议总结")
        print("=" * 60)
        print("""
1. 会话保存优化（最重要）：
   - 减少数据快照大小（从100行减少到10-20行）
   - 使用异步保存（不阻塞主流程）
   - 考虑使用消息队列延迟保存

2. LLM调用优化（效果有限）：
   - 使用更快的模型（如 gemini-2.0-flash-thinking-exp）
   - 缓存常见查询的结果
   - 减少prompt长度

3. 数据库查询优化（当前不需要）：
   - 数据量小（<1000行），查询很快
   - 只有在查询时间 > 1秒时才需要索引
   - 当前瓶颈不在SQL执行

优先级：会话保存 > LLM调用 > SQL查询
        """)
        
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
