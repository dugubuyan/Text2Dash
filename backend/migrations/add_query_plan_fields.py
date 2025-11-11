"""
添加 query_plan 和 data_source_ids 字段到 session_interactions 表

运行方式:
    python -m backend.migrations.add_query_plan_fields
"""
import sys
import os

# 添加项目根目录到 Python 路径
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
            result = session.execute(
                text("SELECT COUNT(*) FROM pragma_table_info('session_interactions') "
                     "WHERE name IN ('query_plan', 'data_source_ids')")
            )
            existing_count = result.scalar()
            
            if existing_count == 2:
                logger.info("字段已存在，跳过迁移")
                return
            
            # 添加 query_plan 字段
            if existing_count == 0 or existing_count == 1:
                logger.info("添加 query_plan 字段...")
                session.execute(
                    text("ALTER TABLE session_interactions ADD COLUMN query_plan TEXT")
                )
                
                logger.info("添加 data_source_ids 字段...")
                session.execute(
                    text("ALTER TABLE session_interactions ADD COLUMN data_source_ids TEXT")
                )
            
            session.commit()
            logger.info("迁移完成！")
            
    except Exception as e:
        logger.error(f"迁移失败: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    migrate()
