#!/usr/bin/env python3
"""
数据库结构分析工具
功能：连接数据库，读取所有表结构，生成AI可读的Markdown文档
用法：python db_schema_analyzer.py <database_url> [output_file]
"""

import sys
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, inspect, MetaData, Table
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError


class DatabaseSchemaAnalyzer:
    """数据库结构分析器"""
    
    def __init__(self, db_url: str):
        """
        初始化分析器
        
        Args:
            db_url: 数据库连接URL
        """
        self.db_url = db_url
        self.engine: Optional[Engine] = None
        self.inspector = None
        self.metadata = MetaData()
        
    def connect(self) -> bool:
        """
        连接到数据库
        
        Returns:
            连接是否成功
        """
        try:
            self.engine = create_engine(self.db_url)
            self.inspector = inspect(self.engine)
            print(f"✓ 成功连接到数据库")
            return True
        except SQLAlchemyError as e:
            print(f"✗ 数据库连接失败: {e}")
            return False
    
    def get_table_names(self) -> List[str]:
        """获取所有表名"""
        return self.inspector.get_table_names()
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        获取表的详细信息
        
        Args:
            table_name: 表名
            
        Returns:
            包含表信息的字典
        """
        columns = self.inspector.get_columns(table_name)
        pk_constraint = self.inspector.get_pk_constraint(table_name)
        foreign_keys = self.inspector.get_foreign_keys(table_name)
        indexes = self.inspector.get_indexes(table_name)
        unique_constraints = self.inspector.get_unique_constraints(table_name)
        
        return {
            'name': table_name,
            'columns': columns,
            'primary_key': pk_constraint,
            'foreign_keys': foreign_keys,
            'indexes': indexes,
            'unique_constraints': unique_constraints
        }
    
    def analyze_table_purpose(self, table_info: Dict[str, Any]) -> str:
        """
        分析表的用途（基于表名和字段推断）
        
        Args:
            table_info: 表信息
            
        Returns:
            表用途描述
        """
        table_name = table_info['name']
        columns = table_info['columns']
        column_names = [col['name'].lower() for col in columns]
        
        # 基于表名推断
        name_lower = table_name.lower()
        
        if 'user' in name_lower or 'account' in name_lower:
            return "用户账户管理"
        elif 'student' in name_lower:
            return "学生信息管理"
        elif 'course' in name_lower or 'class' in name_lower:
            return "课程管理"
        elif 'exam' in name_lower or 'test' in name_lower or 'score' in name_lower:
            return "考试与成绩管理"
        elif 'attendance' in name_lower:
            return "考勤管理"
        elif 'enrollment' in name_lower or 'registration' in name_lower:
            return "选课与注册管理"
        elif 'faculty' in name_lower or 'teacher' in name_lower or 'instructor' in name_lower:
            return "教师管理"
        elif 'department' in name_lower:
            return "院系管理"
        elif 'program' in name_lower or 'major' in name_lower:
            return "专业与项目管理"
        elif 'payment' in name_lower or 'fee' in name_lower or 'tuition' in name_lower:
            return "财务管理"
        elif 'scholarship' in name_lower or 'financial_aid' in name_lower:
            return "奖学金与助学金管理"
        elif 'graduation' in name_lower or 'degree' in name_lower:
            return "毕业与学位管理"
        elif 'session' in name_lower:
            return "会话管理"
        elif 'report' in name_lower:
            return "报告管理"
        elif 'config' in name_lower or 'setting' in name_lower:
            return "配置管理"
        elif 'log' in name_lower or 'audit' in name_lower:
            return "日志与审计"
        elif 'cache' in name_lower:
            return "缓存管理"
        
        # 基于字段推断
        if 'email' in column_names and 'password' in column_names:
            return "认证与授权"
        elif 'created_at' in column_names and 'updated_at' in column_names:
            return "数据记录管理"
        
        return "数据管理"

    def generate_query_suggestions(self, table_info: Dict[str, Any]) -> List[str]:
        """
        生成查询建议（类似function call描述）
        
        Args:
            table_info: 表信息
            
        Returns:
            查询建议列表
        """
        table_name = table_info['name']
        columns = table_info['columns']
        foreign_keys = table_info['foreign_keys']
        
        suggestions = []
        
        # 基础查询
        suggestions.append(f"查询所有{table_name}记录")
        suggestions.append(f"根据ID查询单个{table_name}记录")
        
        # 基于字段的查询
        for col in columns:
            col_name = col['name']
            col_type = str(col['type'])
            
            if 'name' in col_name.lower():
                suggestions.append(f"根据{col_name}搜索{table_name}")
            elif 'date' in col_name.lower():
                suggestions.append(f"根据{col_name}范围筛选{table_name}")
            elif 'status' in col_name.lower():
                suggestions.append(f"根据{col_name}筛选{table_name}")
            elif 'email' in col_name.lower():
                suggestions.append(f"根据{col_name}查找{table_name}")
        
        # 基于外键的关联查询
        for fk in foreign_keys:
            ref_table = fk['referred_table']
            suggestions.append(f"查询{table_name}及其关联的{ref_table}信息")
        
        # 聚合查询
        suggestions.append(f"统计{table_name}总数")
        
        # 时间相关查询
        has_created_at = any(col['name'] in ['created_at', 'created_date', 'date'] for col in columns)
        if has_created_at:
            suggestions.append(f"按时间段统计{table_name}数量")
        
        return suggestions[:8]  # 限制返回数量
    
    def generate_data_examples(self, table_info: Dict[str, Any]) -> str:
        """
        生成数据示例说明
        
        Args:
            table_info: 表信息
            
        Returns:
            数据示例描述
        """
        table_name = table_info['name']
        columns = table_info['columns']
        
        examples = []
        
        # 根据表名生成示例
        name_lower = table_name.lower()
        
        if 'student' in name_lower:
            examples.append("学生基本信息（姓名、学号、入学日期等）")
        elif 'course' in name_lower:
            examples.append("课程信息（课程名称、学分、课程代码等）")
        elif 'exam' in name_lower or 'score' in name_lower:
            examples.append("考试成绩数据（分数、等级、考试日期等）")
        elif 'attendance' in name_lower:
            examples.append("出勤记录（日期、状态、迟到时长等）")
        elif 'enrollment' in name_lower:
            examples.append("选课记录（学生、课程、选课日期等）")
        elif 'faculty' in name_lower or 'teacher' in name_lower:
            examples.append("教师信息（姓名、职称、所属院系等）")
        elif 'payment' in name_lower or 'fee' in name_lower:
            examples.append("缴费记录（金额、日期、支付方式等）")
        elif 'session' in name_lower:
            examples.append("会话数据（会话ID、创建时间、状态等）")
        elif 'report' in name_lower:
            examples.append("报告数据（报告内容、生成时间、类型等）")
        
        # 基于字段类型补充
        for col in columns:
            col_name = col['name']
            if 'json' in str(col['type']).lower():
                examples.append(f"{col_name}字段包含JSON格式的结构化数据")
            elif 'text' in str(col['type']).lower() and 'description' in col_name.lower():
                examples.append(f"{col_name}字段包含详细描述文本")
        
        return "、".join(examples) if examples else "结构化业务数据"
    
    def generate_markdown(self, output_file: str = None) -> str:
        """
        生成Markdown文档
        
        Args:
            output_file: 输出文件路径，如果为None则只返回内容
            
        Returns:
            生成的Markdown内容
        """
        if not self.inspector:
            raise RuntimeError("请先调用connect()方法连接数据库")
        
        table_names = self.get_table_names()
        
        # 开始生成Markdown
        md_lines = []
        md_lines.append("# 数据库结构分析文档")
        md_lines.append("")
        md_lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        md_lines.append(f"**数据库**: {self.db_url.split('/')[-1] if '/' in self.db_url else 'N/A'}")
        md_lines.append(f"**表总数**: {len(table_names)}")
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")
        
        # 目录
        md_lines.append("## 目录")
        md_lines.append("")
        for i, table_name in enumerate(table_names, 1):
            md_lines.append(f"{i}. [{table_name}](#{table_name.lower().replace('_', '-')})")
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")
        
        # 每个表的详细信息
        for table_name in table_names:
            print(f"正在分析表: {table_name}")
            table_info = self.get_table_info(table_name)
            
            md_lines.append(f"## {table_name}")
            md_lines.append("")
            
            # 表用途
            purpose = self.analyze_table_purpose(table_info)
            md_lines.append(f"**用途**: {purpose}")
            md_lines.append("")
            
            # 数据说明
            data_examples = self.generate_data_examples(table_info)
            md_lines.append(f"**数据内容**: {data_examples}")
            md_lines.append("")
            
            # 字段列表
            md_lines.append("### 字段结构")
            md_lines.append("")
            md_lines.append("| 字段名 | 类型 | 可空 | 默认值 | 说明 |")
            md_lines.append("|--------|------|------|--------|------|")
            
            for col in table_info['columns']:
                col_name = col['name']
                col_type = str(col['type'])
                nullable = "是" if col['nullable'] else "否"
                default = str(col['default']) if col['default'] else "-"
                
                # 推断字段说明
                description = self._infer_column_description(col_name, col_type)
                
                md_lines.append(f"| {col_name} | {col_type} | {nullable} | {default} | {description} |")
            
            md_lines.append("")
            
            # 主键
            if table_info['primary_key'] and table_info['primary_key'].get('constrained_columns'):
                pk_cols = ", ".join(table_info['primary_key']['constrained_columns'])
                md_lines.append(f"**主键**: {pk_cols}")
                md_lines.append("")
            
            # 外键关系
            if table_info['foreign_keys']:
                md_lines.append("### 外键关系")
                md_lines.append("")
                for fk in table_info['foreign_keys']:
                    local_cols = ", ".join(fk['constrained_columns'])
                    ref_table = fk['referred_table']
                    ref_cols = ", ".join(fk['referred_columns'])
                    md_lines.append(f"- `{local_cols}` → `{ref_table}.{ref_cols}`")
                md_lines.append("")
            
            # 索引
            if table_info['indexes']:
                md_lines.append("### 索引")
                md_lines.append("")
                for idx in table_info['indexes']:
                    idx_name = idx['name']
                    idx_cols = ", ".join(idx['column_names'])
                    unique = "唯一索引" if idx['unique'] else "普通索引"
                    md_lines.append(f"- `{idx_name}`: {idx_cols} ({unique})")
                md_lines.append("")
            
            # 查询建议（Function Call风格）
            md_lines.append("### 可用查询操作")
            md_lines.append("")
            suggestions = self.generate_query_suggestions(table_info)
            for suggestion in suggestions:
                md_lines.append(f"- {suggestion}")
            md_lines.append("")
            
            md_lines.append("---")
            md_lines.append("")
        
        # 生成关系图说明
        md_lines.append("## 表关系总览")
        md_lines.append("")
        md_lines.append("以下是主要的表关系：")
        md_lines.append("")
        
        for table_name in table_names:
            table_info = self.get_table_info(table_name)
            if table_info['foreign_keys']:
                for fk in table_info['foreign_keys']:
                    ref_table = fk['referred_table']
                    md_lines.append(f"- `{table_name}` → `{ref_table}`")
        
        md_lines.append("")
        
        # 生成完整内容
        content = "\n".join(md_lines)
        
        # 写入文件
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"\n✓ Markdown文档已生成: {output_file}")
        
        return content
    
    def _infer_column_description(self, col_name: str, col_type: str) -> str:
        """
        推断字段说明
        
        Args:
            col_name: 字段名
            col_type: 字段类型
            
        Returns:
            字段说明
        """
        name_lower = col_name.lower()
        
        # 常见字段名映射
        descriptions = {
            'id': '唯一标识符',
            'name': '名称',
            'title': '标题',
            'description': '描述',
            'email': '电子邮件',
            'phone': '电话号码',
            'address': '地址',
            'created_at': '创建时间',
            'updated_at': '更新时间',
            'deleted_at': '删除时间',
            'status': '状态',
            'type': '类型',
            'date': '日期',
            'time': '时间',
            'amount': '金额',
            'price': '价格',
            'quantity': '数量',
            'count': '计数',
            'total': '总计',
            'url': 'URL链接',
            'path': '路径',
            'file': '文件',
            'image': '图片',
            'password': '密码',
            'token': '令牌',
            'key': '键',
            'value': '值',
            'config': '配置',
            'setting': '设置',
            'data': '数据',
            'content': '内容',
            'note': '备注',
            'comment': '评论',
            'score': '分数',
            'grade': '等级',
            'rank': '排名',
            'level': '级别',
        }
        
        # 精确匹配
        if name_lower in descriptions:
            return descriptions[name_lower]
        
        # 模糊匹配
        for key, desc in descriptions.items():
            if key in name_lower:
                return desc
        
        # 基于类型推断
        if 'INT' in col_type.upper():
            return '整数值'
        elif 'VARCHAR' in col_type.upper() or 'TEXT' in col_type.upper():
            return '文本内容'
        elif 'DATE' in col_type.upper():
            return '日期'
        elif 'TIME' in col_type.upper():
            return '时间戳'
        elif 'BOOL' in col_type.upper():
            return '布尔值'
        elif 'DECIMAL' in col_type.upper() or 'FLOAT' in col_type.upper():
            return '数值'
        elif 'JSON' in col_type.upper():
            return 'JSON数据'
        
        return '数据字段'
    
    def close(self):
        """关闭数据库连接"""
        if self.engine:
            self.engine.dispose()
            print("✓ 数据库连接已关闭")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='数据库结构分析工具 - 生成AI可读的Markdown文档',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # SQLite数据库
  python db_schema_analyzer.py sqlite:///./data/config.db
  
  # PostgreSQL数据库
  python db_schema_analyzer.py postgresql://user:password@localhost:5432/dbname
  
  # MySQL数据库
  python db_schema_analyzer.py mysql+pymysql://user:password@localhost:3306/dbname
  
  # 指定输出文件
  python db_schema_analyzer.py sqlite:///./data/config.db output.md
        """
    )
    
    parser.add_argument('db_url', help='数据库连接URL')
    parser.add_argument('output_file', nargs='?', 
                       help='输出Markdown文件路径（默认：db_schema_analysis.md）')
    
    args = parser.parse_args()
    
    # 默认输出文件名
    if not args.output_file:
        # 从数据库URL提取数据库名
        db_name = args.db_url.split('/')[-1].replace('.db', '')
        args.output_file = f"db_schema_analysis_{db_name}.md"
    
    print("=" * 60)
    print("数据库结构分析工具")
    print("=" * 60)
    print(f"数据库URL: {args.db_url}")
    print(f"输出文件: {args.output_file}")
    print("=" * 60)
    print()
    
    # 创建分析器
    analyzer = DatabaseSchemaAnalyzer(args.db_url)
    
    try:
        # 连接数据库
        if not analyzer.connect():
            sys.exit(1)
        
        # 生成文档
        analyzer.generate_markdown(args.output_file)
        
        print()
        print("=" * 60)
        print("✓ 分析完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        analyzer.close()


if __name__ == "__main__":
    main()
