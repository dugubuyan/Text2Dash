"""
测试迁移脚本

在测试数据库上验证迁移过程
"""

import os
import sys
import sqlite3
import tempfile
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from migrate_to_temp_tables import migrate_forward, verify_migration


def create_test_database():
    """创建测试数据库"""
    # 创建临时数据库
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建旧的表结构
    cursor.execute("""
        CREATE TABLE sessions (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE session_interactions (
            id VARCHAR(36) PRIMARY KEY,
            session_id VARCHAR(36) NOT NULL,
            user_query TEXT NOT NULL,
            sql_query TEXT,
            chart_config TEXT,
            summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE report_snapshots (
            id VARCHAR(36) PRIMARY KEY,
            session_id VARCHAR(36) NOT NULL,
            interaction_id VARCHAR(36) NOT NULL,
            data_snapshot TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id),
            FOREIGN KEY (interaction_id) REFERENCES session_interactions(id)
        )
    """)
    
    # 插入测试数据
    cursor.execute("""
        INSERT INTO sessions (id, user_id) 
        VALUES ('test-session-1', 'test-user')
    """)
    
    cursor.execute("""
        INSERT INTO session_interactions (id, session_id, user_query, summary)
        VALUES ('test-interaction-1', 'test-session-1', '测试查询', '测试摘要')
    """)
    
    cursor.execute("""
        INSERT INTO report_snapshots (id, session_id, interaction_id, data_snapshot)
        VALUES ('test-snapshot-1', 'test-session-1', 'test-interaction-1', '[{"test": "data"}]')
    """)
    
    conn.commit()
    conn.close()
    
    return db_path


def test_migration():
    """测试迁移过程"""
    print("=" * 60)
    print("  测试数据库迁移")
    print("=" * 60)
    
    # 创建测试数据库
    print("\n📦 创建测试数据库...")
    db_path = create_test_database()
    print(f"   测试数据库: {db_path}")
    
    # 验证初始状态
    print("\n🔍 验证初始状态...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM report_snapshots")
    snapshot_count = cursor.fetchone()[0]
    print(f"   report_snapshots 记录数: {snapshot_count}")
    
    cursor.execute("PRAGMA table_info(session_interactions)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"   session_interactions 字段: {', '.join(columns)}")
    
    has_temp_table_name = 'temp_table_name' in columns
    print(f"   是否有 temp_table_name 字段: {has_temp_table_name}")
    
    conn.close()
    
    # 执行迁移
    print("\n🚀 执行迁移...")
    success = migrate_forward(db_path)
    
    if not success:
        print("\n❌ 迁移失败")
        os.remove(db_path)
        return False
    
    # 验证迁移结果
    print("\n🔍 验证迁移结果...")
    success = verify_migration(db_path)
    
    if success:
        print("\n✅ 测试通过！")
        print("\n📊 迁移后的数据库状态:")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            ORDER BY name
        """)
        tables = cursor.fetchall()
        print(f"   表列表: {', '.join([t[0] for t in tables])}")
        
        # 检查数据是否保留
        cursor.execute("SELECT COUNT(*) FROM sessions")
        session_count = cursor.fetchone()[0]
        print(f"   sessions 记录数: {session_count}")
        
        cursor.execute("SELECT COUNT(*) FROM session_interactions")
        interaction_count = cursor.fetchone()[0]
        print(f"   session_interactions 记录数: {interaction_count}")
        
        # 检查新字段
        cursor.execute("PRAGMA table_info(session_interactions)")
        columns = cursor.fetchall()
        print(f"\n   session_interactions 表结构:")
        for col in columns:
            print(f"     - {col[1]}: {col[2]}")
        
        conn.close()
    else:
        print("\n❌ 测试失败")
    
    # 清理
    print(f"\n🧹 清理测试数据库: {db_path}")
    os.remove(db_path)
    
    return success


if __name__ == '__main__':
    success = test_migration()
    sys.exit(0 if success else 1)
