"""
测试敏感信息规则解析（带数据库schema）
"""
import asyncio
import os
from backend.services.llm_service import LLMService


async def test_parse_with_schema():
    """测试带数据库schema的敏感信息规则解析"""
    print("\n" + "=" * 60)
    print("测试：带数据库schema的敏感信息规则解析")
    print("=" * 60)
    
    # 模拟数据库schema信息
    db_schema_info = {
        "tables": {
            "students": [
                {"name": "student_id", "type": "INTEGER"},
                {"name": "name", "type": "TEXT"},
                {"name": "id_card_number", "type": "TEXT"},
                {"name": "phone", "type": "TEXT"},
                {"name": "email", "type": "TEXT"},
                {"name": "date_of_birth", "type": "DATE"},
            ],
            "faculty": [
                {"name": "faculty_id", "type": "INTEGER"},
                {"name": "name", "type": "TEXT"},
                {"name": "phone", "type": "TEXT"},
                {"name": "email", "type": "TEXT"},
            ]
        }
    }
    
    llm_service = LLMService()
    
    # 测试用例1：隐藏学生的身份证号和手机号
    print("\n测试用例1：隐藏学生的身份证号和手机号")
    try:
        rule = await llm_service.parse_sensitive_rule(
            natural_language="隐藏学生的身份证号和手机号",
            db_schema_info=db_schema_info
        )
        print(f"✓ 规则名称: {rule.name}")
        print(f"✓ 处理模式: {rule.mode}")
        print(f"✓ 应用列: {rule.columns}")
        print(f"✓ 脱敏模式: {rule.pattern}")
    except Exception as e:
        print(f"✗ 失败: {str(e)}")
    
    # 测试用例2：对所有邮箱进行脱敏
    print("\n测试用例2：对所有邮箱进行脱敏")
    try:
        rule = await llm_service.parse_sensitive_rule(
            natural_language="对所有邮箱进行脱敏",
            db_schema_info=db_schema_info
        )
        print(f"✓ 规则名称: {rule.name}")
        print(f"✓ 处理模式: {rule.mode}")
        print(f"✓ 应用列: {rule.columns}")
        print(f"✓ 脱敏模式: {rule.pattern}")
    except Exception as e:
        print(f"✗ 失败: {str(e)}")
    
    # 测试用例3：使用schema描述文件
    print("\n测试用例3：使用schema描述文件")
    schema_with_description = {
        "schema_description": """
# 医学院校管理系统

## 学生信息表 (students)
- student_id: 学生ID
- name: 姓名
- id_card_number: 身份证号
- phone: 手机号
- email: 邮箱
- date_of_birth: 出生日期

## 教师信息表 (faculty)
- faculty_id: 教师ID
- name: 姓名
- phone: 手机号
- email: 邮箱
"""
    }
    
    try:
        rule = await llm_service.parse_sensitive_rule(
            natural_language="脱敏所有个人联系方式",
            db_schema_info=schema_with_description
        )
        print(f"✓ 规则名称: {rule.name}")
        print(f"✓ 处理模式: {rule.mode}")
        print(f"✓ 应用列: {rule.columns}")
        print(f"✓ 脱敏模式: {rule.pattern}")
    except Exception as e:
        print(f"✗ 失败: {str(e)}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    # 检查是否有API密钥
    if not os.getenv("GEMINI_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        print("警告：未设置 GEMINI_API_KEY 或 OPENAI_API_KEY，测试将跳过")
        print("请设置环境变量后重试")
    else:
        asyncio.run(test_parse_with_schema())
