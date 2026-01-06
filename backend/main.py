"""
商业报表生成器 - 后端主入口
"""
import sys
from pathlib import Path
from contextlib import asynccontextmanager

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from backend.database import init_database
from backend.utils.logger import setup_logger, get_logger
from backend.middleware import TenantMiddleware  # Multi-tenant support
from backend.routes import (
    reports_router,
    sessions_router,
    databases_router,
    mcp_servers_router,
    sensitive_rules_router,
    export_router,
    models_router,
)

# 加载环境变量
load_dotenv()

# 初始化日志
logger = setup_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    # 在多进程模式下，每个worker都会执行此代码
    worker_id = os.getpid()
    logger.info(f"Worker {worker_id} 正在启动...")
    
    try:
        # 初始化数据库
        init_database()
        logger.info(f"Worker {worker_id} 数据库初始化成功")
    except Exception as e:
        logger.error(f"Worker {worker_id} 数据库初始化失败: {e}", exc_info=True)
        raise
    
    logger.info(f"Worker {worker_id} 启动完成")
    
    yield
    
    # 关闭时执行
    logger.info(f"Worker {worker_id} 正在关闭...")


app = FastAPI(
    title="商业报表生成器 API",
    description="基于自然语言的智能数据分析和可视化系统",
    version="1.0.0",
    lifespan=lifespan
)

# 注册路由
app.include_router(reports_router)
app.include_router(sessions_router)
app.include_router(databases_router)
app.include_router(mcp_servers_router)
app.include_router(sensitive_rules_router)
app.include_router(export_router)
app.include_router(models_router)

# 导入并注册缓存路由
from backend.routes.cache import router as cache_router
app.include_router(cache_router)

# === MIDDLEWARE REGISTRATION ===

# Multi-tenant middleware (MUST be added before routes)
app.add_middleware(TenantMiddleware)
logger.info("✓ Multi-tenant middleware registered")

# CORS配置 (including gateway origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # Website
        "http://localhost:3001",   # API Gateway
        "http://localhost:5173",   # Text2Dash frontend (dev)
        "http://localhost:5174",   # Alternative frontend port
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "商业报表生成器 API", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/api/system/db-pool-status")
async def get_db_pool_status():
    """获取数据库连接池状态"""
    from backend.utils.db_monitor import get_pool_status
    return get_pool_status()


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("BACKEND_HOST", "0.0.0.0")
    port = int(os.getenv("BACKEND_PORT", 8000))
    workers = int(os.getenv("BACKEND_WORKERS", 1))
    log_level = os.getenv("LOG_LEVEL", "info").lower()
    
    logger.info(f"启动服务器: {host}:{port}, workers={workers}, log_level={log_level}")
    
    # 使用 workers 或 reload 时都必须传递导入字符串
    if workers > 1:
        # 多进程生产模式
        uvicorn.run(
            "backend.main:app",
            host=host,
            port=port,
            workers=workers,
            log_level=log_level,
            access_log=log_level == "debug"
        )
    else:
        # 单进程开发模式（支持热重载）
        uvicorn.run(
            "backend.main:app",
            host=host,
            port=port,
            log_level=log_level,
            access_log=log_level == "debug",
            reload=True
        )
