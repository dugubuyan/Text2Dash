#!/usr/bin/env python3
"""
数据库结构分析工具 - Python 使用示例
"""

from db_schema_analyzer import DatabaseSchemaAnalyzer


def example_1_basic_usage():
    """示例 1: 基本使用"""
    print("=" * 60)
    print("示例 1: 基本使用 - 分析 SQLite 数据库")
    print("=" * 60)
    
    # 创建分析器
    analyzer = DatabaseSchemaAnalyzer("sqlite:///./data/config.db")
    
    try:
        # 连接数据库
        if analyzer.connect():
            # 生成文档
            analyzer.generate_markdown("config_db_schema.md")
            print("\n✓ 文档已生成: config_db_schema.md")
    finally:
        analyzer.close()
    
    print()


def example_2_get_table_info():
    """示例 2: 获取特定表信息"""
    print("=" * 60)
    print("示例 2: 获取特定表信息")
    print("=" * 60)
    
    analyzer = DatabaseSchemaAnalyzer("sqlite:///./data/config.db")
    
    try:
        if analyzer.connect():
            # 获取所有表名
            tables = analyzer.get_table_names()
            print(f"\n数据库包含 {len(tables)} 个表:")
            for table in tables:
                print(f"  - {table}")
            
            # 获取第一个表的详细信息
            if tables:
                table_name = tables[0]
                print(f"\n表 '{table_name}' 的详细信息:")
                table_info = analyzer.get_table_info(table_name)
                
                print(f"  字段数: {len(table_info['columns'])}")
                print(f"  外键数: {len(table_info['foreign_keys'])}")
                print(f"  索引数: {len(table_info['indexes'])}")
                
                print("\n  字段列表:")
                for col in table_info['columns']:
                    print(f"    - {col['name']}: {col['type']}")
    finally:
        analyzer.close()
    
    print()


def example_3_analyze_purpose():
    """示例 3: 分析表用途"""
    print("=" * 60)
    print("示例 3: 分析表用途和查询建议")
    print("=" * 60)
    
    analyzer = DatabaseSchemaAnalyzer("sqlite:///./data/config.db")
    
    try:
        if analyzer.connect():
            tables = analyzer.get_table_names()
            
            for table_name in tables[:3]:  # 只显示前3个表
                table_info = analyzer.get_table_info(table_name)
                
                print(f"\n表: {table_name}")
                print(f"用途: {analyzer.analyze_table_purpose(table_info)}")
                print(f"数据内容: {analyzer.generate_data_examples(table_info)}")
                
                print("查询建议:")
                suggestions = analyzer.generate_query_suggestions(table_info)
                for suggestion in suggestions[:5]:  # 只显示前5个建议
                    print(f"  - {suggestion}")
    finally:
        analyzer.close()
    
    print()


def example_4_custom_output():
    """示例 4: 自定义输出"""
    print("=" * 60)
    print("示例 4: 生成内容但不写入文件")
    print("=" * 60)
    
    analyzer = DatabaseSchemaAnalyzer("sqlite:///./data/config.db")
    
    try:
        if analyzer.connect():
            # 生成内容但不写入文件
            content = analyzer.generate_markdown()
            
            # 显示前500个字符
            print("\n生成的内容预览:")
            print("-" * 60)
            print(content[:500])
            print("...")
            print("-" * 60)
            print(f"\n总长度: {len(content)} 字符")
    finally:
        analyzer.close()
    
    print()


def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("数据库结构分析工具 - Python 使用示例")
    print("=" * 60 + "\n")
    
    # 运行示例
    example_1_basic_usage()
    example_2_get_table_info()
    example_3_analyze_purpose()
    example_4_custom_output()
    
    print("=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
