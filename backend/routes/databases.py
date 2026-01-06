"""
数据库配置API路由
"""
import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Request  # Added Request
from pydantic import BaseModel, Field

from ..services.database_connector import DatabaseConnector
from ..services.encryption_service import EncryptionService
from ..database import get_database
from ..models.database_config import DatabaseConfig
from ..utils.logger import get_logger
from ..utils.datetime_helper import to_iso_string
from ..utils.tenant_helpers import get_tenant_id  # Added tenant helper

logger = get_logger(__name__)
router = APIRouter(prefix="/api/databases", tags=["databases"])


# ============ Request/Response Models ============

class CreateDatabaseRequest(BaseModel):
    """创建数据库配置请求"""
    name: str = Field(..., description="数据库名称")
    type: str = Field(..., description="数据库类型（sqlite, mysql, postgresql）")
    url: str = Field(..., description="数据库连接URL")
    username: Optional[str] = Field(None, description="用户名")
    password: Optional[str] = Field(None, description="密码")
    use_schema_file: bool = Field(False, description="是否使用schema描述文件")
    schema_description: Optional[str] = Field(None, description="schema描述文件内容")


class UpdateDatabaseRequest(BaseModel):
    """更新数据库配置请求"""
    name: Optional[str] = Field(None, description="数据库名称")
    type: Optional[str] = Field(None, description="数据库类型")
    url: Optional[str] = Field(None, description="数据库连接URL")
    username: Optional[str] = Field(None, description="用户名")
    password: Optional[str] = Field(None, description="密码")
    use_schema_file: Optional[bool] = Field(None, description="是否使用schema描述文件")
    schema_description: Optional[str] = Field(None, description="schema描述文件内容")


class DatabaseResponse(BaseModel):
    """数据库配置响应"""
    id: str
    name: str
    type: str
    url: str
    username: Optional[str]
    use_schema_file: bool
    schema_description: Optional[str]
    created_at: str
    updated_at: str


class ConnectionTestResponse(BaseModel):
    """连接测试响应"""
    success: bool
    message: str
    error: Optional[str] = None


# ============ API Endpoints ============

@router.post("", response_model=DatabaseResponse, status_code=status.HTTP_201_CREATED)
async def create_database_config(request: CreateDatabaseRequest, req: Request):
    """
    创建数据库配置
    """
    try:
        tenant_id = get_tenant_id(req)
        logger.info(f"收到创建数据库配置请求: name={request.name}, type={request.type}, tenant_id={tenant_id}")
        
        db = get_database()
        encryption_service = EncryptionService()
        
        # 加密密码
        encrypted_password = None
        if request.password:
            encrypted_password = encryption_service.encrypt(request.password)
        
        # 创建数据库配置
        config_id = str(uuid.uuid4())
        db_config = DatabaseConfig(
            id=config_id,
            tenant_id=tenant_id,  # Set tenant_id
            name=request.name,
            type=request.type,
            url=request.url,
            username=request.username,
            encrypted_password=encrypted_password,
            use_schema_file=request.use_schema_file,
            schema_description=request.schema_description
        )
        
        with db.get_session() as session:
            session.add(db_config)
            session.commit()
            session.refresh(db_config)
            
            response = DatabaseResponse(
                id=db_config.id,
                name=db_config.name,
                type=db_config.type,
                url=db_config.url,
                username=db_config.username,
                use_schema_file=db_config.use_schema_file,
                schema_description=db_config.schema_description,
                created_at=to_iso_string(db_config.created_at),
                updated_at=to_iso_string(db_config.updated_at)
            )
        
        # 后台异步生成 schema_summary（不阻塞响应）
        import asyncio
        asyncio.create_task(_generate_and_save_schema_summary(config_id))
        
        logger.info(f"数据库配置创建成功: id={config_id}")
        return response
        
    except Exception as e:
        logger.error(f"创建数据库配置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建数据库配置失败: {str(e)}"
        )


@router.get("", response_model=List[DatabaseResponse], status_code=status.HTTP_200_OK)
async def get_database_configs(req: Request):
    """
    获取所有数据库配置
    """
    try:
        logger.info("收到获取数据库配置列表请求")
        
        db = get_database()
        
        tenant_id = get_tenant_id(req)
        
        with db.get_session() as session:
            configs = session.query(DatabaseConfig).filter(
                DatabaseConfig.tenant_id == tenant_id
            ).order_by(DatabaseConfig.created_at.desc()).all()
            
            response = [
                DatabaseResponse(
                    id=config.id,
                    name=config.name,
                    type=config.type,
                    url=config.url,
                    username=config.username,
                    use_schema_file=config.use_schema_file,
                    schema_description=config.schema_description,
                    created_at=to_iso_string(config.created_at),
                    updated_at=to_iso_string(config.updated_at)
                )
                for config in configs
            ]
        
        logger.info(f"返回数据库配置列表: count={len(response)}")
        return response
        
    except Exception as e:
        logger.error(f"获取数据库配置列表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取数据库配置列表失败: {str(e)}"
        )


@router.get("/{config_id}", response_model=DatabaseResponse, status_code=status.HTTP_200_OK)
async def get_database_config(config_id: str, req: Request):
    """
    获取单个数据库配置
    """
    try:
        logger.info(f"收到获取数据库配置请求: id={config_id}")
        
        db = get_database()
        
        tenant_id = get_tenant_id(req)
        
        with db.get_session() as session:
            config = session.query(DatabaseConfig).filter(
                DatabaseConfig.id == config_id,
                DatabaseConfig.tenant_id == tenant_id
            ).first()
            
            if not config:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"数据库配置不存在: {config_id}"
                )
            
            response = DatabaseResponse(
                id=config.id,
                name=config.name,
                type=config.type,
                url=config.url,
                username=config.username,
                use_schema_file=config.use_schema_file,
                schema_description=config.schema_description,
                created_at=to_iso_string(config.created_at),
                updated_at=to_iso_string(config.updated_at)
            )
        
        logger.info(f"返回数据库配置: id={config_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取数据库配置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取数据库配置失败: {str(e)}"
        )


@router.put("/{config_id}", response_model=DatabaseResponse, status_code=status.HTTP_200_OK)
async def update_database_config(config_id: str, request: UpdateDatabaseRequest, req: Request):
    """
    更新数据库配置
    """
    try:
        logger.info(f"收到更新数据库配置请求: id={config_id}")
        
        db = get_database()
        encryption_service = EncryptionService()
        
        tenant_id = get_tenant_id(req)
        
        with db.get_session() as session:
            config = session.query(DatabaseConfig).filter(
                DatabaseConfig.id == config_id,
                DatabaseConfig.tenant_id == tenant_id
            ).first()
            
            if not config:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"数据库配置不存在: {config_id}"
                )
            
            # 更新字段
            if request.name is not None:
                config.name = request.name
            if request.type is not None:
                config.type = request.type
            if request.url is not None:
                config.url = request.url
            if request.username is not None:
                config.username = request.username
            if request.password is not None:
                config.encrypted_password = encryption_service.encrypt(request.password)
            if request.use_schema_file is not None:
                config.use_schema_file = request.use_schema_file
            if request.schema_description is not None:
                config.schema_description = request.schema_description
            
            session.commit()
            session.refresh(config)
            
            response = DatabaseResponse(
                id=config.id,
                name=config.name,
                type=config.type,
                url=config.url,
                username=config.username,
                use_schema_file=config.use_schema_file,
                schema_description=config.schema_description,
                created_at=to_iso_string(config.created_at),
                updated_at=to_iso_string(config.updated_at)
            )
        
        # 如果 schema_description 有变化，重新生成 schema_summary
        if request.schema_description is not None:
            import asyncio
            asyncio.create_task(_generate_and_save_schema_summary(config_id))
        
        logger.info(f"数据库配置更新成功: id={config_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新数据库配置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新数据库配置失败: {str(e)}"
        )


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_database_config(config_id: str, req: Request):
    """
    删除数据库配置
    """
    try:
        logger.info(f"收到删除数据库配置请求: id={config_id}")
        
        db = get_database()
        
        tenant_id = get_tenant_id(req)
        
        with db.get_session() as session:
            config = session.query(DatabaseConfig).filter(
                DatabaseConfig.id == config_id,
                DatabaseConfig.tenant_id == tenant_id
            ).first()
            
            if not config:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"数据库配置不存在: {config_id}"
                )
            
            session.delete(config)
            session.commit()
        
        logger.info(f"数据库配置删除成功: id={config_id}")
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除数据库配置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除数据库配置失败: {str(e)}"
        )


@router.post("/{config_id}/test", response_model=ConnectionTestResponse, status_code=status.HTTP_200_OK)
async def test_database_connection(config_id: str, req: Request):
    """
    测试数据库连接
    """
    try:
        logger.info(f"收到测试数据库连接请求: id={config_id}")
        
        db = get_database()
        
        tenant_id = get_tenant_id(req)
        
        # 获取数据库配置
        with db.get_session() as session:
            config = session.query(DatabaseConfig).filter(
                DatabaseConfig.id == config_id,
                DatabaseConfig.tenant_id == tenant_id
            ).first()
            
            if not config:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"数据库配置不存在: {config_id}"
                )
            
            # 测试连接
            db_connector = DatabaseConnector()
            result = await db_connector.test_connection(config)
            
            response = ConnectionTestResponse(
                success=result.success,
                message=result.message,
                error=result.error
            )
        
        logger.info(f"数据库连接测试完成: id={config_id}, success={result.success}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试数据库连接失败: {str(e)}", exc_info=True)
        return ConnectionTestResponse(
            success=False,
            message="连接测试失败",
            error=str(e)
        )


# ============ 辅助函数 ============

async def _generate_and_save_schema_summary(db_config_id: str):
    """
    后台任务：生成并保存 schema summary
    
    Args:
        db_config_id: 数据库配置ID
    """
    try:
        from ..services.llm_service import LLMService
        from ..services.database_connector import get_database_connector
        
        db = get_database()
        llm = LLMService()
        
        with db.get_session() as session:
            db_config = session.query(DatabaseConfig).filter(
                DatabaseConfig.id == db_config_id
            ).first()
            
            if not db_config:
                logger.warning(f"数据库配置不存在，无法生成概要: {db_config_id}")
                return
            
            # 生成 schema_summary
            if db_config.use_schema_file and db_config.schema_description:
                # 从详细版生成
                logger.info(f"从 schema_description 生成概要: {db_config.name}")
                schema_summary = await llm.generate_schema_summary(
                    schema_description=db_config.schema_description,
                    db_name=db_config.name
                )
            else:
                # 从数据库表名生成
                logger.info(f"从数据库表名生成概要: {db_config.name}")
                try:
                    db_connector = get_database_connector()
                    schema_info = await db_connector.get_schema_info(db_config_id)
                    table_names = list(schema_info.tables.keys())
                    
                    schema_summary = await llm.generate_schema_summary_from_tables(
                        table_names=table_names,
                        db_name=db_config.name
                    )
                except Exception as e:
                    logger.error(f"从数据库获取表名失败: {e}")
                    schema_summary = f"# {db_config.name}\n\n数据库概要生成失败。"
            
            # 保存
            db_config.schema_summary = schema_summary
            session.commit()
            
            logger.info(f"Schema summary 自动生成成功: {db_config_id}")
            
    except Exception as e:
        logger.error(f"自动生成 schema summary 失败: {e}", exc_info=True)
