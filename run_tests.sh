#!/bin/bash
# 回归测试快捷脚本

# 激活虚拟环境
source venv/bin/activate

# 运行测试
python backend/tests/run_all_tests.py "$@"
