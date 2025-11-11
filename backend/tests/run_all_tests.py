#!/usr/bin/env python
"""
回归测试运行器
运行所有测试以确保系统整体正确性

使用方法:
    python backend/tests/run_all_tests.py
    python backend/tests/run_all_tests.py --quick  # 只运行快速测试
    python backend/tests/run_all_tests.py --full   # 运行所有测试（包括需要API的）
"""
import sys
import os
import asyncio
import argparse
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """打印标题"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}\n")


def print_test_result(test_name, passed, duration=None):
    """打印测试结果"""
    status = f"{Colors.GREEN}✓ PASSED{Colors.RESET}" if passed else f"{Colors.RED}✗ FAILED{Colors.RESET}"
    duration_str = f" ({duration:.2f}s)" if duration else ""
    print(f"{status} - {test_name}{duration_str}")


def run_test_file(test_file, test_name):
    """运行单个测试文件"""
    import subprocess
    import time
    
    start_time = time.time()
    try:
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            timeout=60
        )
        duration = time.time() - start_time
        passed = result.returncode == 0
        
        if not passed:
            print(f"\n{Colors.YELLOW}错误输出:{Colors.RESET}")
            print(result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)
        
        return passed, duration
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        print(f"\n{Colors.RED}测试超时 (>60s){Colors.RESET}")
        return False, duration
    except Exception as e:
        duration = time.time() - start_time
        print(f"\n{Colors.RED}测试执行失败: {e}{Colors.RESET}")
        return False, duration


def run_pytest_tests(test_file, test_name):
    """运行pytest测试"""
    import subprocess
    import time
    
    start_time = time.time()
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=60
        )
        duration = time.time() - start_time
        passed = result.returncode == 0
        
        if not passed:
            print(f"\n{Colors.YELLOW}错误输出:{Colors.RESET}")
            print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
        
        return passed, duration
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        print(f"\n{Colors.RED}测试超时 (>60s){Colors.RESET}")
        return False, duration
    except Exception as e:
        duration = time.time() - start_time
        print(f"\n{Colors.RED}测试执行失败: {e}{Colors.RESET}")
        return False, duration


def check_requirements():
    """检查测试环境"""
    print(f"{Colors.BOLD}检查测试环境...{Colors.RESET}")
    
    issues = []
    
    # 检查虚拟环境
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        issues.append("⚠ 未激活虚拟环境")
    else:
        print(f"  {Colors.GREEN}✓{Colors.RESET} 虚拟环境已激活")
    
    # 检查关键依赖
    try:
        import litellm
        print(f"  {Colors.GREEN}✓{Colors.RESET} litellm 已安装")
    except ImportError:
        issues.append("✗ litellm 未安装")
    
    try:
        import sqlalchemy
        print(f"  {Colors.GREEN}✓{Colors.RESET} sqlalchemy 已安装")
    except ImportError:
        issues.append("✗ sqlalchemy 未安装")
    
    # 检查API密钥（可选）
    from dotenv import load_dotenv
    load_dotenv()
    
    has_api_key = bool(os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY"))
    if has_api_key:
        print(f"  {Colors.GREEN}✓{Colors.RESET} LLM API密钥已配置")
    else:
        print(f"  {Colors.YELLOW}⚠{Colors.RESET} LLM API密钥未配置（部分测试将跳过）")
    
    if issues:
        print(f"\n{Colors.RED}环境问题:{Colors.RESET}")
        for issue in issues:
            print(f"  {issue}")
        return False
    
    print(f"{Colors.GREEN}环境检查通过！{Colors.RESET}\n")
    return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='运行回归测试')
    parser.add_argument('--quick', action='store_true', help='只运行快速测试（不需要外部依赖）')
    parser.add_argument('--full', action='store_true', help='运行所有测试（包括需要API的）')
    parser.add_argument('--skip-env-check', action='store_true', help='跳过环境检查')
    args = parser.parse_args()
    
    print_header("回归测试套件")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 检查环境
    if not args.skip_env_check:
        if not check_requirements():
            print(f"\n{Colors.RED}环境检查失败，请先解决上述问题{Colors.RESET}")
            return 1
    
    tests_dir = Path(__file__).parent
    
    # 定义测试分组
    quick_tests = [
        ("test_mcp_connector.py", "MCP连接器测试", "normal"),
        ("test_filter_service.py", "敏感信息过滤服务测试", "normal"),
        ("test_data_source_manager.py", "数据源管理器测试", "normal"),
    ]
    
    database_tests = [
        ("test_database_connector.py", "数据库连接器测试", "normal"),
        ("test_infrastructure.py", "基础设施测试", "normal"),
    ]
    
    api_tests = [
        ("test_llm_service.py", "LLM服务测试", "normal"),
        ("test_session_manager.py", "会话管理器测试", "normal"),
        ("test_sensitive_rule_e2e.py", "敏感规则端到端测试", "normal"),
    ]
    
    pytest_tests = [
        ("test_report_service.py", "报表服务测试", "pytest"),
        ("test_export_service.py", "导出服务测试", "pytest"),
    ]
    
    integration_tests = [
        ("test_e2e_integration.py", "端到端集成测试", "pytest"),
        ("test_session_temp_table.py", "Session临时表测试", "normal"),
    ]
    
    performance_tests = [
        ("test_performance.py", "性能测试", "normal"),
    ]
    
    # 根据参数选择要运行的测试
    if args.quick:
        test_groups = [
            ("快速测试", quick_tests),
        ]
    elif args.full:
        test_groups = [
            ("快速测试", quick_tests),
            ("数据库测试", database_tests),
            ("API测试", api_tests),
            ("Pytest测试", pytest_tests),
            ("集成测试", integration_tests),
            ("性能测试", performance_tests),
        ]
    else:
        # 默认运行快速测试和数据库测试
        test_groups = [
            ("快速测试", quick_tests),
            ("数据库测试", database_tests),
        ]
    
    # 运行测试
    all_results = []
    total_duration = 0
    
    for group_name, tests in test_groups:
        print(f"\n{Colors.BOLD}{group_name}{Colors.RESET}")
        print("-" * 70)
        
        for test_file, test_name, test_type in tests:
            test_path = tests_dir / test_file
            
            if not test_path.exists():
                print_test_result(test_name, False)
                print(f"  {Colors.YELLOW}文件不存在: {test_file}{Colors.RESET}")
                all_results.append((test_name, False, 0))
                continue
            
            if test_type == "pytest":
                passed, duration = run_pytest_tests(str(test_path), test_name)
            else:
                passed, duration = run_test_file(str(test_path), test_name)
            
            print_test_result(test_name, passed, duration)
            all_results.append((test_name, passed, duration))
            total_duration += duration
    
    # 打印总结
    print_header("测试总结")
    
    passed_count = sum(1 for _, passed, _ in all_results if passed)
    total_count = len(all_results)
    
    print(f"总测试数: {total_count}")
    print(f"{Colors.GREEN}通过: {passed_count}{Colors.RESET}")
    print(f"{Colors.RED}失败: {total_count - passed_count}{Colors.RESET}")
    print(f"总耗时: {total_duration:.2f}秒")
    
    if passed_count == total_count:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ 所有测试通过！{Colors.RESET}")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ 部分测试失败{Colors.RESET}")
        print(f"\n{Colors.YELLOW}失败的测试:{Colors.RESET}")
        for test_name, passed, _ in all_results:
            if not passed:
                print(f"  - {test_name}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
