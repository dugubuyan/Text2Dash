"""
会话管理器测试
"""
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 加载环境变量
load_dotenv()

from backend.database import Database
from backend.services.session_manager import SessionManager
from backend.services.llm_service import LLMService
from backend.services.dto import ConversationMessage


async def test_session_manager():
    """测试会话管理器的核心功能"""
    
    print("=" * 60)
    print("会话管理器测试")
    print("=" * 60)
    
    # 使用测试数据库
    test_db_path = "./data/test_session.db"
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    
    db = Database(f"sqlite:///{test_db_path}")
    db.create_tables()
    
    # 初始化会话管理器（使用本地mem0）
    session_manager = SessionManager(database=db, use_mem0=True)
    
    print("\n1. 测试创建会话")
    print("-" * 60)
    session_id = await session_manager.create_session(user_id="test_user_001")
    print(f"✓ 创建会话成功: {session_id}")
    
    print("\n2. 测试获取会话信息")
    print("-" * 60)
    session_info = await session_manager.get_session_info(session_id)
    print(f"✓ 会话信息: {session_info}")
    
    print("\n3. 测试添加交互记录")
    print("-" * 60)
    
    # 添加第一个交互
    interaction_id_1 = await session_manager.add_interaction(
        session_id=session_id,
        user_query="显示2023年所有学生的平均成绩",
        sql_query="SELECT AVG(score) FROM students WHERE year = 2023",
        chart_config={
            "type": "bar",
            "title": "2023年平均成绩"
        },
        summary="2023年学生平均成绩为85.5分"
    )
    print(f"✓ 添加交互1: {interaction_id_1}")
    
    # 添加第二个交互
    interaction_id_2 = await session_manager.add_interaction(
        session_id=session_id,
        user_query="按专业分组显示",
        sql_query="SELECT major, AVG(score) FROM students WHERE year = 2023 GROUP BY major",
        chart_config={
            "type": "bar",
            "title": "各专业平均成绩"
        },
        summary="计算机专业平均分最高，为88.2分"
    )
    print(f"✓ 添加交互2: {interaction_id_2}")
    
    print("\n4. 测试获取会话上下文")
    print("-" * 60)
    context = await session_manager.get_context(session_id)
    print(f"✓ 获取到 {len(context)} 条上下文消息")
    for i, msg in enumerate(context, 1):
        print(f"  消息{i}: [{msg.role}] {msg.content[:50]}...")
    
    print("\n5. 测试获取会话历史")
    print("-" * 60)
    history = await session_manager.get_session_history(session_id, limit=10)
    print(f"✓ 获取到 {len(history)} 条历史记录")
    for i, record in enumerate(history, 1):
        print(f"  记录{i}: {record['user_query'][:50]}...")
    
    print("\n6. 测试上下文压缩（模拟）")
    print("-" * 60)
    
    # 添加更多交互以触发压缩阈值
    for i in range(3, 12):
        await session_manager.add_interaction(
            session_id=session_id,
            user_query=f"测试查询 {i}",
            summary=f"测试结果 {i}"
        )
    
    print(f"✓ 添加了 9 条额外交互，总共 11 条")
    
    # 获取更新后的上下文
    context_after = await session_manager.get_context(session_id)
    print(f"✓ 当前上下文消息数: {len(context_after)}")
    
    # 测试压缩（需要LLM服务，这里只测试逻辑）
    if os.getenv("LITELLM_API_KEY") or os.getenv("GEMINI_API_KEY"):
        print("\n  尝试使用LLM压缩上下文...")
        llm_service = LLMService()
        compressed = await session_manager.check_and_compress(session_id, llm_service)
        print(f"  {'✓' if compressed else '✗'} 压缩{'成功' if compressed else '未执行（可能未超过阈值）'}")
    else:
        print("  ⚠ 跳过LLM压缩测试（未配置API密钥）")
    
    print("\n7. 测试删除会话")
    print("-" * 60)
    deleted = await session_manager.delete_session(session_id)
    print(f"✓ 删除会话: {'成功' if deleted else '失败'}")
    
    # 验证删除
    session_info_after = await session_manager.get_session_info(session_id)
    print(f"✓ 验证删除: 会话{'不存在' if session_info_after is None else '仍存在'}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    
    # 清理测试数据库
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
        print("\n✓ 清理测试数据库")


if __name__ == "__main__":
    asyncio.run(test_session_manager())
