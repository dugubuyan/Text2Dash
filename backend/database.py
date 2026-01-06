"""
数据库初始化和连接管理
"""
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator

from .models.base import Base
from .models import (
    DatabaseConfig,
    MCPServerConfig,
    SensitiveRule,
    SavedReport,
    Session,
    SessionInteraction,
    ReportSnapshot,
)


class Database:
    """数据库管理类"""
    
    def __init__(self, db_url: str = None):
        """
        初始化数据库连接
        
        Args:
            db_url: 数据库URL，如果为None则从环境变量读取
        """
        if db_url is None:
            # 获取项目根目录 (text2dash/)
            # database.py is in text2dash/backend/
            project_root = Path(__file__).resolve().parent.parent
            default_db_path = project_root / "data" / "config.db"
            
            db_path = os.getenv("CONFIG_DB_PATH", str(default_db_path))
            # 确保data目录存在
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            db_url = f"sqlite:///{db_path}"
        
        # 优化连接池配置
        pool_config = {
            "poolclass": QueuePool,
            "pool_size": 20,  # 增加连接池大小
            "max_overflow": 40,  # 增加最大溢出连接数
            "pool_timeout": 30,
            "pool_recycle": 3600,  # 1小时后回收连接，避免连接过期
            "pool_pre_ping": True,  # 使用前检查连接是否有效
            "echo": False,  # 关闭SQL日志以提升性能
        }
        
        # SQLite特殊配置
        if db_url.startswith("sqlite"):
            pool_config["connect_args"] = {"check_same_thread": False}
        
        self.engine = create_engine(db_url, **pool_config)
        
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
            expire_on_commit=False  # 提交后不过期对象，减少查询
        )
    
    def create_tables(self):
        """创建所有表"""
        Base.metadata.create_all(bind=self.engine)
    
    def drop_tables(self):
        """删除所有表（谨慎使用）"""
        Base.metadata.drop_all(bind=self.engine)
    
    @contextmanager
    def get_session(self) -> Generator[SQLAlchemySession, None, None]:
        """
        获取数据库会话的上下文管理器
        
        Yields:
            SQLAlchemy会话对象
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


# 全局数据库实例
_db_instance = None


def get_database() -> Database:
    """获取全局数据库实例"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance


def init_database():
    """初始化数据库（创建所有表）"""
    db = get_database()
    db.create_tables()
    print("数据库初始化完成")


def get_db_session() -> Generator[SQLAlchemySession, None, None]:
    """
    FastAPI依赖注入函数：获取数据库会话
    
    使用方式：
        @app.get("/items")
        def read_items(db: Session = Depends(get_db_session)):
            return db.query(Item).all()
    
    Yields:
        SQLAlchemy会话对象
    """
    db = get_database()
    session = db.SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    # 直接运行此脚本时初始化数据库
    init_database()
