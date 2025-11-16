#!/usr/bin/env python3
"""
估算单次查询的 Token 使用量
模拟实际的 LLM 调用，计算 prompt 和 response 的 token 数
"""

import sys
import os

# 添加父目录到路径以导入 token_counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from token_counter import TokenCounter


def build_query_plan_prompt(query: str, schema_content: str) -> str:
    """构建查询计划的完整 prompt（模拟 LLMService._build_query_plan_system_prompt）"""
    
    system_prompt = f"""你是数据查询规划专家，根据用户查询生成执行计划。

可用数据源：

## 数据库

### 数据库ID: test_medical_db
名称: Medical School Database
**类型: SQLITE**
数据库结构描述:
{schema_content}

返回JSON格式：

{{
  "no_data_source_match": false,
  "user_message": null,
  "sql_queries": [
    {{
      "db_config_id": "数据库ID或'__session__'（临时表）",
      "sql": "SQL查询语句",
      "source_alias": "结果别名"
    }}
  ],
  "mcp_calls": [
    {{
      "mcp_config_id": "MCP Server ID",
      "tool_name": "工具名称",
      "parameters": {{"参数名": "参数值"}},
      "source_alias": "结果别名"
    }}
  ],
  "needs_combination": true/false,
  "combination_strategy": "组合策略说明（如需要）"
}}

核心规则：

1. **数据源选择**：
   - 查询临时表：db_config_id="__session__"
   - 查询数据库：使用对应的 db_config_id
   - 查询与所有数据源无关时：设置 no_data_source_match=true

2. **SQL生成**：
   - 只生成 SELECT 查询
   - **根据数据库类型使用对应的SQL方言**（注意不同数据库的语法差异）
   - 多步骤查询使用子查询或 CTE，禁止引用其他查询的 source_alias
   - 聚合函数必须指定别名（如 COUNT(*) AS total_count）

3. **数据组合**：仅当跨数据库或跨MCP源时，设置 needs_combination=true
"""
    
    user_message = f"请为以下查询生成执行计划：\n\n{query}"
    
    return system_prompt, user_message


def estimate_response_tokens(query_type: str) -> int:
    """估算响应的 token 数（基于典型响应）"""
    
    # 典型的响应示例
    typical_responses = {
        "simple": """{
  "no_data_source_match": false,
  "user_message": null,
  "sql_queries": [
    {
      "db_config_id": "test_medical_db",
      "sql": "SELECT a.name AS advisor_name, COUNT(saa.student_id) AS student_count FROM academic_advisors aa JOIN faculty a ON aa.faculty_id = a.faculty_id LEFT JOIN student_advisor_assignments saa ON aa.advisor_id = saa.advisor_id GROUP BY aa.advisor_id, a.name ORDER BY student_count DESC",
      "source_alias": "advisor_student_counts"
    }
  ],
  "mcp_calls": [],
  "needs_combination": false,
  "combination_strategy": null
}""",
        "complex": """{
  "no_data_source_match": false,
  "user_message": null,
  "sql_queries": [
    {
      "db_config_id": "test_medical_db",
      "sql": "SELECT s.name, s.student_id, AVG(es.score) as avg_score FROM students s JOIN student_enrollments se ON s.student_id = se.student_id JOIN exam_scores es ON se.enrollment_id = es.enrollment_id WHERE se.status = 'Completed' GROUP BY s.student_id, s.name HAVING avg_score > 80 ORDER BY avg_score DESC",
      "source_alias": "high_performers"
    },
    {
      "db_config_id": "test_medical_db",
      "sql": "SELECT d.department_name, COUNT(DISTINCT s.student_id) as student_count FROM departments d JOIN majors m ON d.department_id = m.department_id JOIN student_majors sm ON m.major_id = sm.major_id JOIN students s ON sm.student_id = s.student_id GROUP BY d.department_id, d.department_name",
      "source_alias": "department_stats"
    }
  ],
  "mcp_calls": [],
  "needs_combination": true,
  "combination_strategy": "Join high_performers with department_stats to show top students by department"
}"""
    }
    
    return typical_responses.get(query_type, typical_responses["simple"])


def main():
    # 初始化 token counter
    counter = TokenCounter()
    
    # 读取 schema
    schema_path = "data/test_medical_db_schema_compact.md"
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_content = f.read()
    
    # 测试多个查询场景
    test_queries = [
        ("简单查询", "展示每位导师所带学生数量的对比"),
        ("复杂查询", "分析各个系的学生成绩分布，包括平均分、最高分、最低分，并按平均分排序"),
        ("多表关联", "查询临床实习评分最高的前10名学生，包括他们的导师信息、专业和GPA")
    ]
    
    print("="*100)
    print("查询 Token 使用量估算 - 多场景对比")
    print("="*100)
    
    all_results = []
    
    for query_type, test_query in test_queries:
        print(f"\n{'='*100}")
        print(f"场景: {query_type}")
        print(f"查询: {test_query}")
        print('='*100)
        
        # 构建 prompt
        system_prompt, user_message = build_query_plan_prompt(test_query, schema_content)
    
        # 计算各部分的 token
        system_tokens = counter.count_tokens(system_prompt)
        user_tokens = counter.count_tokens(user_message)
        
        # 估算响应 token（根据查询复杂度）
        response_type = "complex" if "复杂" in query_type or "多表" in query_type else "simple"
        typical_response = estimate_response_tokens(response_type)
        response_tokens = counter.count_tokens(typical_response)
        
        # 总计
        total_input_tokens = system_tokens + user_tokens
        total_tokens = total_input_tokens + response_tokens
        
        print(f"\n{'组件':<30} {'Token 数':>15} {'占比':>10}")
        print("-"*80)
        print(f"{'System Prompt (含 Schema)':<30} {system_tokens:>15,} {system_tokens/total_tokens*100:>9.1f}%")
        print(f"{'User Message (查询)':<30} {user_tokens:>15,} {user_tokens/total_tokens*100:>9.1f}%")
        print(f"{'输入总计':<30} {total_input_tokens:>15,} {total_input_tokens/total_tokens*100:>9.1f}%")
        print(f"{'LLM Response (估算)':<30} {response_tokens:>15,} {response_tokens/total_tokens*100:>9.1f}%")
        print("-"*80)
        print(f"{'总计':<30} {total_tokens:>15,} {'100.0%':>10}")
        
        # 成本估算
        # GPT-4 Turbo: $0.01/1K input, $0.03/1K output
        input_cost_gpt4 = (total_input_tokens / 1000) * 0.01
        output_cost_gpt4 = (response_tokens / 1000) * 0.03
        total_cost_gpt4 = input_cost_gpt4 + output_cost_gpt4
        
        # Gemini 2.0 Flash: $0.00001875/1K input, $0.000075/1K output
        input_cost_gemini = (total_input_tokens / 1000) * 0.00001875
        output_cost_gemini = (response_tokens / 1000) * 0.000075
        total_cost_gemini = input_cost_gemini + output_cost_gemini
        
        # DeepSeek: ¥2/1M input (=$0.002/1K), ¥3/1M output (=$0.003/1K)
        # 按 1 USD = 7.2 CNY 换算
        input_cost_deepseek_cny = (total_input_tokens / 1000000) * 2
        output_cost_deepseek_cny = (response_tokens / 1000000) * 3
        total_cost_deepseek_cny = input_cost_deepseek_cny + output_cost_deepseek_cny
        
        input_cost_deepseek_usd = input_cost_deepseek_cny / 7.2
        output_cost_deepseek_usd = output_cost_deepseek_cny / 7.2
        total_cost_deepseek_usd = total_cost_deepseek_cny / 7.2
        
        print(f"\n成本 (GPT-4 Turbo): ${total_cost_gpt4:.6f} | 1000次: ${total_cost_gpt4*1000:.2f}")
        print(f"成本 (Gemini 2.0 Flash): ${total_cost_gemini:.8f} | 1000次: ${total_cost_gemini*1000:.4f}")
        print(f"成本 (DeepSeek): ¥{total_cost_deepseek_cny:.6f} (${total_cost_deepseek_usd:.8f}) | 1000次: ¥{total_cost_deepseek_cny*1000:.4f}")
        
        all_results.append({
            'type': query_type,
            'query': test_query,
            'system_tokens': system_tokens,
            'user_tokens': user_tokens,
            'response_tokens': response_tokens,
            'total_tokens': total_tokens,
            'cost_gpt4': total_cost_gpt4,
            'cost_gemini': total_cost_gemini,
            'cost_deepseek_cny': total_cost_deepseek_cny,
            'cost_deepseek_usd': total_cost_deepseek_usd
        })
    
    # 汇总对比
    print(f"\n{'='*120}")
    print("场景对比汇总")
    print('='*120)
    print(f"{'场景':<15} {'输入Tokens':>12} {'输出Tokens':>12} {'总Tokens':>12} {'GPT-4':>12} {'Gemini':>15} {'DeepSeek(¥)':>15}")
    print("-"*120)
    for r in all_results:
        print(f"{r['type']:<15} {r['system_tokens']+r['user_tokens']:>12,} {r['response_tokens']:>12,} "
              f"{r['total_tokens']:>12,} ${r['cost_gpt4']:>10.6f} ${r['cost_gemini']:>13.8f} "
              f"¥{r['cost_deepseek_cny']:>13.6f}")
    print("="*120)
    
    # Schema 详细分析
    print(f"\nSchema Token 详情:")
    print(f"  - Schema 文件大小: {len(schema_content):,} 字符")
    print(f"  - Schema Token 数: {counter.count_tokens(schema_content):,}")
    schema_ratio = counter.count_tokens(schema_content) / all_results[0]['system_tokens'] * 100
    print(f"  - Schema 在 System Prompt 中的占比: {schema_ratio:.1f}%")
    
    # 优化建议
    avg_total = sum(r['total_tokens'] for r in all_results) / len(all_results)
    avg_cost_gpt4 = sum(r['cost_gpt4'] for r in all_results) / len(all_results)
    avg_cost_gemini = sum(r['cost_gemini'] for r in all_results) / len(all_results)
    avg_cost_deepseek_cny = sum(r['cost_deepseek_cny'] for r in all_results) / len(all_results)
    avg_cost_deepseek_usd = sum(r['cost_deepseek_usd'] for r in all_results) / len(all_results)
    
    print(f"\n模型成本对比 (平均每次查询):")
    print(f"  - GPT-4 Turbo:      ${avg_cost_gpt4:.6f}  (基准)")
    print(f"  - Gemini 2.0 Flash: ${avg_cost_gemini:.8f}  (便宜 {avg_cost_gpt4/avg_cost_gemini:.0f}x)")
    print(f"  - DeepSeek:         ¥{avg_cost_deepseek_cny:.6f} (${avg_cost_deepseek_usd:.8f})  (便宜 {avg_cost_gpt4/avg_cost_deepseek_usd:.0f}x)")
    
    print(f"\n1000次查询成本对比:")
    print(f"  - GPT-4 Turbo:      ${avg_cost_gpt4*1000:.2f}")
    print(f"  - Gemini 2.0 Flash: ${avg_cost_gemini*1000:.4f}")
    print(f"  - DeepSeek:         ¥{avg_cost_deepseek_cny*1000:.4f} (${avg_cost_deepseek_usd*1000:.4f})")
    
    print(f"\n优化建议:")
    print(f"  1. Schema 压缩: 当前 schema 占用 {counter.count_tokens(schema_content):,} tokens ({schema_ratio:.1f}% 的输入)")
    print(f"     - 可以进一步精简表描述")
    print(f"     - 只包含查询相关的表信息（动态过滤）")
    print(f"  2. 启用缓存: 相同查询可以直接返回缓存结果，节省 100% token")
    print(f"  3. 模型选择: DeepSeek 性价比最高，适合高频查询场景")
    print(f"  4. 平均每次查询: {avg_total:.0f} tokens")
    
    print("\n" + "="*120)


if __name__ == '__main__':
    main()
