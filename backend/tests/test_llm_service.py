"""
LLM服务测试脚本
"""
import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from backend.services import LLMService, DataMetadata, ConversationMessage


async def test_llm_service_initialization():
    """测试LLM服务初始化"""
    print("\n测试1: LLM服务初始化")
    try:
        llm_service = LLMService()
        print(f"✓ LLM服务初始化成功")
        print(f"  默认模型: {llm_service.default_model}")
        print(f"  最大重试次数: {llm_service.max_retries}")
        return True
    except Exception as e:
        print(f"✗ LLM服务初始化失败: {e}")
        return False


async def test_data_structures():
    """测试数据结构"""
    print("\n测试2: 数据结构创建")
    try:
        # 测试DataMetadata
        metadata = DataMetadata(
            columns=["name", "age", "score"],
            column_types={"name": "string", "age": "integer", "score": "float"},
            row_count=100
        )
        print(f"✓ DataMetadata创建成功: {len(metadata.columns)} 列, {metadata.row_count} 行")
        
        # 测试ConversationMessage
        message = ConversationMessage(
            role="user",
            content="显示所有学生的平均成绩"
        )
        print(f"✓ ConversationMessage创建成功: role={message.role}")
        
        return True
    except Exception as e:
        print(f"✗ 数据结构创建失败: {e}")
        return False


async def test_llm_methods_exist():
    """测试LLM服务方法是否存在"""
    print("\n测试3: LLM服务方法检查")
    try:
        llm_service = LLMService()
        
        methods = [
            "generate_query_plan",
            "generate_combination_sql",
            "analyze_data_and_suggest_chart",
            "summarize_conversation",
            "parse_sensitive_rule",
        ]
        
        for method in methods:
            if hasattr(llm_service, method):
                print(f"✓ 方法存在: {method}")
            else:
                print(f"✗ 方法缺失: {method}")
                return False
        
        return True
    except Exception as e:
        print(f"✗ 方法检查失败: {e}")
        return False


async def test_parse_sensitive_rule_simple():
    """测试解析简单的敏感信息规则"""
    print("\n测试4: 解析简单敏感信息规则（手机号脱敏）")
    try:
        llm_service = LLMService()
        
        # 测试手机号脱敏
        rule = await llm_service.parse_sensitive_rule(
            "手机号只显示前3位和后4位",
            available_columns=["id", "name", "phone", "email"]
        )
        
        print(f"✓ 规则解析成功")
        print(f"  规则名称: {rule.name}")
        print(f"  处理模式: {rule.mode}")
        print(f"  目标列: {rule.columns}")
        print(f"  脱敏模式: {rule.pattern}")
        
        # 验证结果
        assert rule.mode == "mask", "模式应该是mask"
        assert "phone" in rule.columns or "手机号" in rule.columns, "应该包含phone列"
        assert rule.pattern is not None, "应该有脱敏模式"
        
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_parse_sensitive_rule_custom():
    """测试解析自定义敏感信息规则"""
    print("\n测试5: 解析自定义敏感信息规则（银行卡号）")
    try:
        llm_service = LLMService()
        
        # 测试银行卡号脱敏
        rule = await llm_service.parse_sensitive_rule(
            "银行卡号保留前4位和后4位，中间用星号替换",
            available_columns=["id", "name", "card_number", "balance"]
        )
        
        print(f"✓ 规则解析成功")
        print(f"  规则名称: {rule.name}")
        print(f"  处理模式: {rule.mode}")
        print(f"  目标列: {rule.columns}")
        print(f"  脱敏模式: {rule.pattern}")
        
        # 验证结果
        assert rule.mode == "mask", "模式应该是mask"
        assert "card_number" in rule.columns or "银行卡号" in rule.columns, "应该包含card_number列"
        
        # 检查是否是JSON格式的自定义规则
        if rule.pattern and rule.pattern.startswith('{'):
            import json
            pattern_obj = json.loads(rule.pattern)
            print(f"  解析的JSON规则: {pattern_obj}")
            assert pattern_obj.get("type") == "custom", "应该是custom类型"
            assert pattern_obj.get("keep_start") == 4, "应该保留前4位"
            assert pattern_obj.get("keep_end") == 4, "应该保留后4位"
        
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_parse_sensitive_rule_filter():
    """测试解析过滤规则"""
    print("\n测试6: 解析过滤规则（隐藏敏感列）")
    try:
        llm_service = LLMService()
        
        # 测试完全隐藏
        rule = await llm_service.parse_sensitive_rule(
            "隐藏身份证号和密码",
            available_columns=["id", "name", "id_card", "password", "email"]
        )
        
        print(f"✓ 规则解析成功")
        print(f"  规则名称: {rule.name}")
        print(f"  处理模式: {rule.mode}")
        print(f"  目标列: {rule.columns}")
        print(f"  脱敏模式: {rule.pattern}")
        
        # 验证结果
        assert rule.mode == "filter", "模式应该是filter"
        assert any(col in rule.columns for col in ["id_card", "身份证号", "password", "密码"]), "应该包含敏感列"
        assert rule.pattern is None, "filter模式不应该有pattern"
        
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_parse_sensitive_rule_regex():
    """测试解析正则表达式规则"""
    print("\n测试7: 解析正则表达式规则（替换数字）")
    try:
        llm_service = LLMService()
        
        # 测试正则替换
        rule = await llm_service.parse_sensitive_rule(
            "工资数据将所有数字替换为X",
            available_columns=["id", "name", "salary", "department"]
        )
        
        print(f"✓ 规则解析成功")
        print(f"  规则名称: {rule.name}")
        print(f"  处理模式: {rule.mode}")
        print(f"  目标列: {rule.columns}")
        print(f"  脱敏模式: {rule.pattern}")
        
        # 验证结果
        assert rule.mode == "mask", "模式应该是mask"
        assert "salary" in rule.columns or "工资" in rule.columns, "应该包含salary列"
        
        # 检查是否是JSON格式的regex规则
        if rule.pattern and rule.pattern.startswith('{'):
            import json
            pattern_obj = json.loads(rule.pattern)
            print(f"  解析的JSON规则: {pattern_obj}")
            assert pattern_obj.get("type") == "regex", "应该是regex类型"
        
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("LLM服务测试")
    print("=" * 60)
    
    results = []
    
    # 运行基础测试
    results.append(await test_llm_service_initialization())
    results.append(await test_data_structures())
    results.append(await test_llm_methods_exist())
    
    # 运行敏感信息规则解析测试（需要API密钥）
    if os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY"):
        print("\n" + "=" * 60)
        print("敏感信息规则解析测试（需要LLM API）")
        print("=" * 60)
        results.append(await test_parse_sensitive_rule_simple())
        results.append(await test_parse_sensitive_rule_custom())
        results.append(await test_parse_sensitive_rule_filter())
        results.append(await test_parse_sensitive_rule_regex())
    else:
        print("\n⚠ 跳过LLM API测试（未配置API密钥）")
    
    # 总结
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("✓ 所有测试通过！")
    else:
        print("✗ 部分测试失败")
    
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
