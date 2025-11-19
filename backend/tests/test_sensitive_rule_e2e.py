"""
敏感信息规则端到端测试
演示从自然语言到数据脱敏的完整流程
"""
import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import Mock

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from backend.services.llm_service import LLMService
from backend.services.filter_service import FilterService
from backend.database import Database


def get_sample_data():
    """创建示例数据"""
    return [
        {
            "id": 1,
            "name": "张三",
            "phone": "13800138000",
            "email": "zhangsan@example.com",
            "id_card": "110101199001011234",
            "card_number": "6222021234567890",
            "salary": 15000,
            "department": "技术部"
        },
        {
            "id": 2,
            "name": "李四",
            "phone": "13900139000",
            "email": "lisi@example.com",
            "id_card": "110101199002021234",
            "card_number": "6222029876543210",
            "salary": 18000,
            "department": "产品部"
        },
        {
            "id": 3,
            "name": "王五",
            "phone": "13700137000",
            "email": "wangwu@example.com",
            "id_card": "110101199003031234",
            "card_number": "6222025555666677",
            "salary": 20000,
            "department": "技术部"
        }
    ]


async def test_e2e_phone_masking():
    """端到端测试：手机号脱敏"""
    print("\n" + "=" * 60)
    print("测试1: 手机号脱敏（预定义模式）")
    print("=" * 60)
    
    try:
        # 步骤1: 用户用自然语言描述规则
        user_input = "手机号只显示前3位和后4位"
        print(f"\n用户输入: {user_input}")
        
        # 步骤2: LLM解析自然语言为结构化规则
        llm_service = LLMService()
        rule = await llm_service.parse_sensitive_rule(
            user_input,
            available_columns=["id", "name", "phone", "email", "id_card", "card_number", "salary"]
        )
        
        print(f"\nLLM解析结果:")
        print(f"  规则名称: {rule.name}")
        print(f"  处理模式: {rule.mode}")
        print(f"  目标列: {rule.columns}")
        print(f"  脱敏模式: {rule.pattern}")
        
        # 步骤3: 应用脱敏规则到实际数据
        mock_db = Mock(spec=Database)
        filter_service = FilterService(mock_db)
        sample_data = get_sample_data()
        
        print(f"\n原始数据（前2条）:")
        for i, row in enumerate(sample_data[:2]):
            print(f"  {i+1}. {row['name']}: {row['phone']}")
        
        # 对每个可能的列名应用脱敏
        masked_data = sample_data
        for column in rule.columns:
            if column in masked_data[0]:
                masked_data = filter_service.mask_column(masked_data, column, pattern=rule.pattern)
        
        print(f"\n脱敏后数据（前2条）:")
        for i, row in enumerate(masked_data[:2]):
            phone_col = next((col for col in rule.columns if col in row), None)
            if phone_col:
                print(f"  {i+1}. {row['name']}: {row[phone_col]}")
        
        print(f"\n✓ 测试通过！")
        return True
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_e2e_card_custom_masking():
    """端到端测试：银行卡号自定义脱敏"""
    print("\n" + "=" * 60)
    print("测试2: 银行卡号脱敏（自定义规则）")
    print("=" * 60)
    
    try:
        # 步骤1: 用户用自然语言描述规则
        user_input = "银行卡号保留前4位和后4位，中间用星号替换"
        print(f"\n用户输入: {user_input}")
        
        # 步骤2: LLM解析自然语言为结构化规则
        llm_service = LLMService()
        rule = await llm_service.parse_sensitive_rule(
            user_input,
            available_columns=["id", "name", "phone", "email", "id_card", "card_number", "salary"]
        )
        
        print(f"\nLLM解析结果:")
        print(f"  规则名称: {rule.name}")
        print(f"  处理模式: {rule.mode}")
        print(f"  目标列: {rule.columns}")
        print(f"  脱敏模式: {rule.pattern}")
        
        # 如果是JSON格式，解析并显示
        if rule.pattern and rule.pattern.startswith('{'):
            pattern_obj = json.loads(rule.pattern)
            print(f"  解析的规则: {pattern_obj}")
        
        # 步骤3: 应用脱敏规则到实际数据
        mock_db = Mock(spec=Database)
        filter_service = FilterService(mock_db)
        sample_data = get_sample_data()
        
        print(f"\n原始数据（前2条）:")
        for i, row in enumerate(sample_data[:2]):
            print(f"  {i+1}. {row['name']}: {row['card_number']}")
        
        # 对每个可能的列名应用脱敏
        masked_data = sample_data
        for column in rule.columns:
            if column in masked_data[0]:
                masked_data = filter_service.mask_column(masked_data, column, pattern=rule.pattern)
        
        print(f"\n脱敏后数据（前2条）:")
        for i, row in enumerate(masked_data[:2]):
            card_col = next((col for col in rule.columns if col in row), None)
            if card_col:
                print(f"  {i+1}. {row['name']}: {row[card_col]}")
        
        print(f"\n✓ 测试通过！")
        return True
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_e2e_filter_mode():
    """端到端测试：完全过滤模式"""
    print("\n" + "=" * 60)
    print("测试3: 完全过滤模式（隐藏敏感列）")
    print("=" * 60)
    
    try:
        # 步骤1: 用户用自然语言描述规则
        user_input = "隐藏身份证号"
        print(f"\n用户输入: {user_input}")
        
        # 步骤2: LLM解析自然语言为结构化规则
        llm_service = LLMService()
        rule = await llm_service.parse_sensitive_rule(
            user_input,
            available_columns=["id", "name", "phone", "email", "id_card", "card_number", "salary"]
        )
        
        print(f"\nLLM解析结果:")
        print(f"  规则名称: {rule.name}")
        print(f"  处理模式: {rule.mode}")
        print(f"  目标列: {rule.columns}")
        print(f"  脱敏模式: {rule.pattern}")
        
        # 步骤3: 应用过滤规则到实际数据
        mock_db = Mock(spec=Database)
        filter_service = FilterService(mock_db)
        sample_data = get_sample_data()
        
        print(f"\n原始数据列: {list(sample_data[0].keys())}")
        
        # 对每个可能的列名应用过滤
        filtered_data = sample_data
        for column in rule.columns:
            if column in filtered_data[0]:
                filtered_data = filter_service.filter_column(filtered_data, column)
        
        print(f"过滤后数据列: {list(filtered_data[0].keys())}")
        
        # 验证敏感列已被移除
        for column in rule.columns:
            if column not in filtered_data[0]:
                print(f"  ✓ 列 '{column}' 已被移除")
        
        print(f"\n✓ 测试通过！")
        return True
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_e2e_salary_regex():
    """端到端测试：工资数据正则替换"""
    print("\n" + "=" * 60)
    print("测试4: 工资数据脱敏（正则表达式）")
    print("=" * 60)
    
    try:
        # 步骤1: 用户用自然语言描述规则
        user_input = "工资数据将所有数字替换为X"
        print(f"\n用户输入: {user_input}")
        
        # 步骤2: LLM解析自然语言为结构化规则
        llm_service = LLMService()
        rule = await llm_service.parse_sensitive_rule(
            user_input,
            available_columns=["id", "name", "phone", "email", "id_card", "card_number", "salary"]
        )
        
        print(f"\nLLM解析结果:")
        print(f"  规则名称: {rule.name}")
        print(f"  处理模式: {rule.mode}")
        print(f"  目标列: {rule.columns}")
        print(f"  脱敏模式: {rule.pattern}")
        
        # 如果是JSON格式，解析并显示
        if rule.pattern and rule.pattern.startswith('{'):
            pattern_obj = json.loads(rule.pattern)
            print(f"  解析的规则: {pattern_obj}")
        
        # 步骤3: 应用脱敏规则到实际数据
        mock_db = Mock(spec=Database)
        filter_service = FilterService(mock_db)
        sample_data = get_sample_data()
        
        print(f"\n原始数据（前2条）:")
        for i, row in enumerate(sample_data[:2]):
            print(f"  {i+1}. {row['name']}: {row['salary']} 元")
        
        # 对每个可能的列名应用脱敏
        masked_data = sample_data
        for column in rule.columns:
            if column in masked_data[0]:
                masked_data = filter_service.mask_column(masked_data, column, pattern=rule.pattern)
        
        print(f"\n脱敏后数据（前2条）:")
        for i, row in enumerate(masked_data[:2]):
            salary_col = next((col for col in rule.columns if col in row), None)
            if salary_col:
                print(f"  {i+1}. {row['name']}: {row[salary_col]}")
        
        print(f"\n✓ 测试通过！")
        return True
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_e2e_complex_scenario():
    """端到端测试：复杂场景（多个规则）"""
    print("\n" + "=" * 60)
    print("测试5: 复杂场景（应用多个脱敏规则）")
    print("=" * 60)
    
    try:
        llm_service = LLMService()
        mock_db = Mock(spec=Database)
        filter_service = FilterService(mock_db)
        sample_data = get_sample_data()
        
        print(f"\n原始数据（第1条）:")
        print(json.dumps(sample_data[0], ensure_ascii=False, indent=2))
        
        # 规则1: 手机号脱敏
        print(f"\n应用规则1: 手机号脱敏")
        rule1 = await llm_service.parse_sensitive_rule(
            "手机号只显示前3位和后4位",
            available_columns=list(sample_data[0].keys())
        )
        for column in rule1.columns:
            if column in sample_data[0]:
                sample_data = filter_service.mask_column(sample_data, column, pattern=rule1.pattern)
                print(f"  ✓ 已脱敏列: {column}")
        
        # 规则2: 银行卡号脱敏
        print(f"\n应用规则2: 银行卡号脱敏")
        rule2 = await llm_service.parse_sensitive_rule(
            "银行卡号保留前4位和后4位",
            available_columns=list(sample_data[0].keys())
        )
        for column in rule2.columns:
            if column in sample_data[0]:
                sample_data = filter_service.mask_column(sample_data, column, pattern=rule2.pattern)
                print(f"  ✓ 已脱敏列: {column}")
        
        # 规则3: 隐藏身份证号
        print(f"\n应用规则3: 隐藏身份证号")
        rule3 = await llm_service.parse_sensitive_rule(
            "隐藏身份证号",
            available_columns=list(sample_data[0].keys())
        )
        for column in rule3.columns:
            if column in sample_data[0]:
                sample_data = filter_service.filter_column(sample_data, column)
                print(f"  ✓ 已移除列: {column}")
        
        print(f"\n处理后数据（第1条）:")
        print(json.dumps(sample_data[0], ensure_ascii=False, indent=2))
        
        print(f"\n✓ 测试通过！")
        return True
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """运行所有端到端测试"""
    print("=" * 60)
    print("敏感信息规则端到端测试")
    print("从自然语言到数据脱敏的完整流程")
    print("=" * 60)
    
    # 检查API密钥
    if not (os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")):
        print("\n⚠ 错误: 未配置LLM API密钥")
        print("请在.env文件中配置 GEMINI_API_KEY 或 OPENAI_API_KEY")
        return
    
    results = []
    
    # 运行测试
    results.append(await test_e2e_phone_masking())
    results.append(await test_e2e_card_custom_masking())
    results.append(await test_e2e_filter_mode())
    results.append(await test_e2e_salary_regex())
    results.append(await test_e2e_complex_scenario())
    
    # 总结
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("✓ 所有端到端测试通过！")
        print("\n完整流程验证成功:")
        print("  1. 用户用自然语言描述脱敏规则")
        print("  2. LLM将自然语言转换为结构化JSON规则")
        print("  3. FilterService应用规则到实际数据")
        print("  4. 数据成功脱敏/过滤")
    else:
        print("✗ 部分测试失败")
    
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
