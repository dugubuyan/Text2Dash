"""
添加数据库配置的schema描述字段

运行方式：
python -m backend.migrations.add_schema_description_fields
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlalchemy import text
from backend.database import get_database
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def migrate():
    """执行迁移"""
    db = get_database()
    
    try:
        with db.get_session() as session:
            # 检查字段是否已存在
            result = session.execute(text(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='database_configs'"
            )).fetchone()
            
            if result:
                table_sql = result[0]
                logger.info(f"当前表结构: {table_sql}")
                
                # 检查是否已有新字段
                if 'use_schema_file' in table_sql and 'schema_description' in table_sql:
                    logger.info("字段已存在，无需迁移")
                    return
            
            # 添加新字段
            logger.info("开始添加schema描述字段...")
            
            # 添加 use_schema_file 字段
            try:
                session.execute(text(
                    "ALTER TABLE database_configs ADD COLUMN use_schema_file BOOLEAN DEFAULT 0 NOT NULL"
                ))
                logger.info("添加 use_schema_file 字段成功")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    logger.info("use_schema_file 字段已存在")
                else:
                    raise
            
            # 添加 schema_description 字段
            try:
                session.execute(text(
                    "ALTER TABLE database_configs ADD COLUMN schema_description TEXT"
                ))
                logger.info("添加 schema_description 字段成功")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    logger.info("schema_description 字段已存在")
                else:
                    raise
            
            session.commit()
            logger.info("迁移完成！")
            
    except Exception as e:
        logger.error(f"迁移失败: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    logger.info("开始执行数据库迁移：添加schema描述字段")
    migrate()
    logger.info("迁移执行完成")
