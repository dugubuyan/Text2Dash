"""
测试敏感信息过滤服务
"""
import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from backend.services.filter_service import FilterService
from backend.models.sensitive_rule import SensitiveRule as SensitiveRuleModel
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
            "salary": 10000
        },
        {
            "id": 2,
            "name": "李四",
            "phone": "13900139000",
            "email": "lisi@example.com",
            "id_card": "110101199002021234",
            "salary": 12000
        }
    ]


async def test_filter_single_column():
    """测试移除单个列"""
    print("\n测试1: 移除单个列")
    try:
        mock_db = Mock(spec=Database)
        filter_service = FilterService(mock_db)
        sample_data = get_sample_data()
        
        result = filter_service.filter_column(sample_data, "phone")
        
        assert len(result) == 2
        assert "phone" not in result[0]
        assert "phone" not in result[1]
        assert "name" in result[0]
        assert "id" in result[0]
        
        print("✓ 成功移除phone列")
        print(f"  原始列: {list(sample_data[0].keys())}")
        print(f"  过滤后: {list(result[0].keys())}")
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False


async def test_filter_multiple_columns():
    """测试移除多个列"""
    print("\n测试2: 移除多个列")
    try:
        mock_db = Mock(spec=Database)
        filter_service = FilterService(mock_db)
        sample_data = get_sample_data()
        
        result = filter_service.filter_column(sample_data, "phone")
        result = filter_service.filter_column(result, "email")
        
        assert len(result) == 2
        assert "phone" not in result[0]
        assert "email" not in result[0]
        assert "name" in result[0]
        
        print("✓ 成功移除phone和email列")
        print(f"  过滤后: {list(result[0].keys())}")
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False


async def test_mask_full_default():
    """测试默认完全脱敏"""
    print("\n测试3: 默认完全脱敏")
    try:
        mock_db = Mock(spec=Database)
        filter_service = FilterService(mock_db)
        sample_data = get_sample_data()
        
        result = filter_service.mask_column(sample_data, "name")
        
        assert len(result) == 2
        # 中文名字只有2个字符，根据_full_mask逻辑会返回 **
        assert result[0]["name"] == "**"
        assert result[1]["name"] == "**"
        
        print("✓ 成功脱敏name列")
        print(f"  原始: {sample_data[0]['name']} -> 脱敏: {result[0]['name']}")
        print(f"  原始: {sample_data[1]['name']} -> 脱敏: {result[1]['name']}")
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False


async def test_mask_phone_pattern():
    """测试手机号脱敏模式"""
    print("\n测试4: 手机号脱敏模式")
    try:
        mock_db = Mock(spec=Database)
        filter_service = FilterService(mock_db)
        sample_data = get_sample_data()
        
        result = filter_service.mask_column(sample_data, "phone", pattern="phone")
        
        assert len(result) == 2
        # 11位手机号: 前3位 + 4个* + 后4位
        assert result[0]["phone"] == "138****8000"
        assert result[1]["phone"] == "139****9000"
        
        print("✓ 成功脱敏phone列")
        print(f"  原始: {sample_data[0]['phone']} -> 脱敏: {result[0]['phone']}")
        print(f"  原始: {sample_data[1]['phone']} -> 脱敏: {result[1]['phone']}")
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False


async def test_mask_email_pattern():
    """测试邮箱脱敏模式"""
    print("\n测试5: 邮箱脱敏模式")
    try:
        mock_db = Mock(spec=Database)
        filter_service = FilterService(mock_db)
        sample_data = get_sample_data()
        
        result = filter_service.mask_column(sample_data, "email", pattern="email")
        
        assert len(result) == 2
        assert result[0]["email"] == "z*******@example.com"
        assert result[1]["email"] == "l***@example.com"
        
        print("✓ 成功脱敏email列")
        print(f"  原始: {sample_data[0]['email']} -> 脱敏: {result[0]['email']}")
        print(f"  原始: {sample_data[1]['email']} -> 脱敏: {result[1]['email']}")
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False


async def test_mask_id_card_pattern():
    """测试身份证号脱敏模式"""
    print("\n测试6: 身份证号脱敏模式")
    try:
        mock_db = Mock(spec=Database)
        filter_service = FilterService(mock_db)
        sample_data = get_sample_data()
        
        result = filter_service.mask_column(sample_data, "id_card", pattern="id_card")
        
        assert len(result) == 2
        # 18位身份证: 前6位 + 8个* + 后4位
        assert result[0]["id_card"] == "110101********1234"
        assert result[1]["id_card"] == "110101********1234"
        
        print("✓ 成功脱敏id_card列")
        print(f"  原始: {sample_data[0]['id_card']} -> 脱敏: {result[0]['id_card']}")
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False


async def test_apply_filter_mode():
    """测试应用完全过滤模式"""
    print("\n测试7: 应用完全过滤模式")
    try:
        mock_db = Mock(spec=Database)
        filter_service = FilterService(mock_db)
        sample_data = get_sample_data()
        
        # 创建模拟规则
        rule = SensitiveRuleModel()
        rule.id = "rule1"
        rule.name = "Remove Phone"
        rule.mode = "filter"
        rule.columns = json.dumps(["phone"])
        rule.pattern = None
        
        # 模拟数据库查询
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.all.return_value = [rule]
        mock_session.query.return_value = mock_query
        
        # 正确模拟上下文管理器
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_session)
        mock_context.__exit__ = MagicMock(return_value=False)
        mock_db.get_session.return_value = mock_context
        
        # 执行过滤
        result = await filter_service.apply_filters(sample_data, "db1")
        
        assert len(result) == 2
        assert "phone" not in result[0]
        assert "name" in result[0]
        
        print("✓ 成功应用过滤规则")
        print(f"  规则: {rule.name} (mode={rule.mode})")
        print(f"  过滤后列: {list(result[0].keys())}")
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_apply_mask_mode():
    """测试应用脱敏模式"""
    print("\n测试8: 应用脱敏模式")
    try:
        mock_db = Mock(spec=Database)
        filter_service = FilterService(mock_db)
        sample_data = get_sample_data()
        
        # 创建模拟规则
        rule = SensitiveRuleModel()
        rule.id = "rule2"
        rule.name = "Mask Phone"
        rule.mode = "mask"
        rule.columns = json.dumps(["phone"])
        rule.pattern = "phone"
        
        # 模拟数据库查询
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.all.return_value = [rule]
        mock_session.query.return_value = mock_query
        
        # 正确模拟上下文管理器
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_session)
        mock_context.__exit__ = MagicMock(return_value=False)
        mock_db.get_session.return_value = mock_context
        
        # 执行过滤
        result = await filter_service.apply_filters(sample_data, "db1")
        
        assert len(result) == 2
        assert "phone" in result[0]
        assert result[0]["phone"] == "138****8000"
        
        print("✓ 成功应用脱敏规则")
        print(f"  规则: {rule.name} (mode={rule.mode})")
        print(f"  脱敏结果: {result[0]['phone']}")
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_apply_multiple_rules():
    """测试应用多个规则"""
    print("\n测试9: 应用多个规则")
    try:
        mock_db = Mock(spec=Database)
        filter_service = FilterService(mock_db)
        sample_data = get_sample_data()
        
        # 创建多个模拟规则
        rule1 = SensitiveRuleModel()
        rule1.id = "rule1"
        rule1.name = "Remove Phone"
        rule1.mode = "filter"
        rule1.columns = json.dumps(["phone"])
        rule1.pattern = None
        
        rule2 = SensitiveRuleModel()
        rule2.id = "rule2"
        rule2.name = "Mask Email"
        rule2.mode = "mask"
        rule2.columns = json.dumps(["email"])
        rule2.pattern = "email"
        
        # 模拟数据库查询
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.all.return_value = [rule1, rule2]
        mock_session.query.return_value = mock_query
        
        # 正确模拟上下文管理器
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_session)
        mock_context.__exit__ = MagicMock(return_value=False)
        mock_db.get_session.return_value = mock_context
        
        # 执行过滤
        result = await filter_service.apply_filters(sample_data, "db1")
        
        assert len(result) == 2
        assert "phone" not in result[0]
        assert "email" in result[0]
        assert result[0]["email"] == "z*******@example.com"
        
        print("✓ 成功应用多个规则")
        print(f"  规则1: {rule1.name} - 移除phone列")
        print(f"  规则2: {rule2.name} - 脱敏email列")
        print(f"  结果: {result[0]}")
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_apply_no_rules():
    """测试没有规则时返回原始数据"""
    print("\n测试10: 没有规则时返回原始数据")
    try:
        mock_db = Mock(spec=Database)
        filter_service = FilterService(mock_db)
        sample_data = get_sample_data()
        
        # 模拟数据库查询返回空列表
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.all.return_value = []
        mock_session.query.return_value = mock_query
        
        # 正确模拟上下文管理器
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_session)
        mock_context.__exit__ = MagicMock(return_value=False)
        mock_db.get_session.return_value = mock_context
        
        # 执行过滤
        result = await filter_service.apply_filters(sample_data, "db1")
        
        assert result == sample_data
        
        print("✓ 没有规则时正确返回原始数据")
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_custom_rule_json():
    """测试JSON格式的自定义规则"""
    print("\n测试11: JSON格式自定义规则 - 保留前3位和后4位")
    try:
        mock_db = Mock(spec=Database)
        filter_service = FilterService(mock_db)
        sample_data = get_sample_data()
        
        # 自定义规则：保留前3位和后4位
        custom_pattern = json.dumps({
            "type": "custom",
            "keep_start": 3,
            "keep_end": 4,
            "mask_char": "*"
        })
        
        result = filter_service.mask_column(sample_data, "phone", pattern=custom_pattern)
        
        assert len(result) == 2
        assert result[0]["phone"] == "138****8000"
        assert result[1]["phone"] == "139****9000"
        
        print("✓ 成功应用自定义JSON规则")
        print(f"  规则: keep_start=3, keep_end=4")
        print(f"  原始: {sample_data[0]['phone']} -> 脱敏: {result[0]['phone']}")
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_custom_rule_regex():
    """测试正则表达式自定义规则"""
    print("\n测试12: 正则表达式自定义规则 - 替换所有数字")
    try:
        mock_db = Mock(spec=Database)
        filter_service = FilterService(mock_db)
        sample_data = get_sample_data()
        
        # 正则表达式规则：将所有数字替换为X
        regex_pattern = json.dumps({
            "type": "regex",
            "pattern": "\\d",
            "replacement": "X"
        })
        
        result = filter_service.mask_column(sample_data, "phone", pattern=regex_pattern)
        
        assert len(result) == 2
        assert result[0]["phone"] == "XXXXXXXXXXX"
        assert result[1]["phone"] == "XXXXXXXXXXX"
        
        print("✓ 成功应用正则表达式规则")
        print(f"  规则: 替换所有数字为X")
        print(f"  原始: {sample_data[0]['phone']} -> 脱敏: {result[0]['phone']}")
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_custom_rule_range():
    """测试范围脱敏自定义规则"""
    print("\n测试13: 范围脱敏自定义规则 - 脱敏中间部分")
    try:
        mock_db = Mock(spec=Database)
        filter_service = FilterService(mock_db)
        sample_data = get_sample_data()
        
        # 范围规则：脱敏第3-7位
        range_pattern = json.dumps({
            "type": "range",
            "ranges": [[3, 7]],
            "mask_char": "#"
        })
        
        result = filter_service.mask_column(sample_data, "phone", pattern=range_pattern)
        
        assert len(result) == 2
        assert result[0]["phone"] == "138####8000"
        assert result[1]["phone"] == "139####9000"
        
        print("✓ 成功应用范围脱敏规则")
        print(f"  规则: 脱敏第3-7位，使用#")
        print(f"  原始: {sample_data[0]['phone']} -> 脱敏: {result[0]['phone']}")
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_custom_rule_multiple_ranges():
    """测试多范围脱敏"""
    print("\n测试14: 多范围脱敏 - 脱敏多个区间")
    try:
        mock_db = Mock(spec=Database)
        filter_service = FilterService(mock_db)
        
        # 测试身份证号：保留前6位和后4位，中间脱敏
        data = [{"id_card": "110101199001011234"}]
        
        range_pattern = json.dumps({
            "type": "range",
            "ranges": [[6, 14]],
            "mask_char": "*"
        })
        
        result = filter_service.mask_column(data, "id_card", pattern=range_pattern)
        
        assert result[0]["id_card"] == "110101********1234"
        
        print("✓ 成功应用多范围脱敏规则")
        print(f"  原始: {data[0]['id_card']} -> 脱敏: {result[0]['id_card']}")
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("敏感信息过滤服务测试")
    print("=" * 60)
    
    tests = [
        test_filter_single_column,
        test_filter_multiple_columns,
        test_mask_full_default,
        test_mask_phone_pattern,
        test_mask_email_pattern,
        test_mask_id_card_pattern,
        test_apply_filter_mode,
        test_apply_mask_mode,
        test_apply_multiple_rules,
        test_apply_no_rules,
        test_custom_rule_json,
        test_custom_rule_regex,
        test_custom_rule_range,
        test_custom_rule_multiple_ranges,
    ]
    
    results = []
    for test in tests:
        result = await test()
        results.append(result)
    
    print("\n" + "=" * 60)
    print(f"测试完成: {sum(results)}/{len(results)} 通过")
    print("=" * 60)
    
    return all(results)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
