"""
MCP Server配置API路由
"""
import json
import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Request  # Added Request
from pydantic import BaseModel, Field

from ..services.mcp_connector import MCPConnector
from ..services.encryption_service import EncryptionService
from ..database import get_database
from ..models.mcp_server_config import MCPServerConfig
from ..utils.logger import get_logger
from ..utils.datetime_helper import to_iso_string
from ..utils.tenant_helpers import get_tenant_id  # Added tenant helper

logger = get_logger(__name__)
router = APIRouter(prefix="/api/mcp-servers", tags=["mcp-servers"])


# ============ Request/Response Models ============

class CreateMCPServerRequest(BaseModel):
    """创建MCP Server配置请求"""
    name: str = Field(..., description="MCP Server名称")
    url: str = Field(..., description="MCP Server URL")
    auth_type: Optional[str] = Field("none", description="认证类型（none, bearer, api_key）")
    auth_token: Optional[str] = Field(None, description="认证令牌")


class UpdateMCPServerRequest(BaseModel):
    """更新MCP Server配置请求"""
    name: Optional[str] = Field(None, description="MCP Server名称")
    url: Optional[str] = Field(None, description="MCP Server URL")
    auth_type: Optional[str] = Field(None, description="认证类型")
    auth_token: Optional[str] = Field(None, description="认证令牌")


class MCPToolResponse(BaseModel):
    """MCP工具响应"""
    name: str
    description: str
    parameters: dict


class MCPServerResponse(BaseModel):
    """MCP Server配置响应"""
    id: str
    name: str
    url: str
    auth_type: Optional[str]
    available_tools: Optional[List[MCPToolResponse]]
    created_at: str
    updated_at: str


class ConnectionTestResponse(BaseModel):
    """连接测试响应"""
    success: bool
    message: str
    error: Optional[str] = None


# ============ API Endpoints ============

@router.post("", response_model=MCPServerResponse, status_code=status.HTTP_201_CREATED)
async def create_mcp_server_config(request: CreateMCPServerRequest, req: Request):
    """
    创建MCP Server配置
    """
    try:
        logger.info(f"收到创建MCP Server配置请求: name={request.name}, url={request.url}")
        
        db = get_database()
        encryption_service = EncryptionService()
        
        # 加密认证令牌
        encrypted_token = None
        if request.auth_token:
            encrypted_token = encryption_service.encrypt(request.auth_token)
        
        tenant_id = get_tenant_id(req)
        
        # 创建MCP Server配置
        config_id = str(uuid.uuid4())
        mcp_config = MCPServerConfig(
            id=config_id,
            tenant_id=tenant_id,  # Set tenant_id
            name=request.name,
            url=request.url,
            auth_type=request.auth_type,
            encrypted_auth_token=encrypted_token,
            available_tools=None  # 将在测试连接时获取
        )
        
        with db.get_session() as session:
            session.add(mcp_config)
            session.commit()
            session.refresh(mcp_config)
            
            response = MCPServerResponse(
                id=mcp_config.id,
                name=mcp_config.name,
                url=mcp_config.url,
                auth_type=mcp_config.auth_type,
                available_tools=None,
                created_at=to_iso_string(config.created_at),
                updated_at=to_iso_string(config.updated_at)
            )
        
        logger.info(f"MCP Server配置创建成功: id={config_id}")
        return response
        
    except Exception as e:
        logger.error(f"创建MCP Server配置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建MCP Server配置失败: {str(e)}"
        )


@router.get("", response_model=List[MCPServerResponse], status_code=status.HTTP_200_OK)
async def get_mcp_server_configs(req: Request):
    """
    获取所有MCP Server配置
    """
    try:
        logger.info("收到获取MCP Server配置列表请求")
        
        db = get_database()
        
        tenant_id = get_tenant_id(req)
        
        with db.get_session() as session:
            configs = session.query(MCPServerConfig).filter(
                MCPServerConfig.tenant_id == tenant_id
            ).order_by(MCPServerConfig.created_at.desc()).all()
            
            response = [
                MCPServerResponse(
                    id=config.id,
                    name=config.name,
                    url=config.url,
                    auth_type=config.auth_type,
                    available_tools=[
                        MCPToolResponse(**tool)
                        for tool in json.loads(config.available_tools)
                    ] if config.available_tools else None,
                    created_at=to_iso_string(config.created_at),
                    updated_at=to_iso_string(config.updated_at)
                )
                for config in configs
            ]
        
        logger.info(f"返回MCP Server配置列表: count={len(response)}")
        return response
        
    except Exception as e:
        logger.error(f"获取MCP Server配置列表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取MCP Server配置列表失败: {str(e)}"
        )


@router.get("/{config_id}", response_model=MCPServerResponse, status_code=status.HTTP_200_OK)
async def get_mcp_server_config(config_id: str, req: Request):
    """
    获取单个MCP Server配置
    """
    try:
        logger.info(f"收到获取MCP Server配置请求: id={config_id}")
        
        db = get_database()
        
        tenant_id = get_tenant_id(req)
        
        with db.get_session() as session:
            config = session.query(MCPServerConfig).filter(
                MCPServerConfig.id == config_id,
                MCPServerConfig.tenant_id == tenant_id
            ).first()
            
            if not config:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"MCP Server配置不存在: {config_id}"
                )
            
            response = MCPServerResponse(
                id=config.id,
                name=config.name,
                url=config.url,
                auth_type=config.auth_type,
                available_tools=[
                    MCPToolResponse(**tool)
                    for tool in json.loads(config.available_tools)
                ] if config.available_tools else None,
                created_at=to_iso_string(config.created_at),
                updated_at=to_iso_string(config.updated_at)
            )
        
        logger.info(f"返回MCP Server配置: id={config_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取MCP Server配置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取MCP Server配置失败: {str(e)}"
        )


@router.put("/{config_id}", response_model=MCPServerResponse, status_code=status.HTTP_200_OK)
async def update_mcp_server_config(config_id: str, request: UpdateMCPServerRequest, req: Request):
    """
    更新MCP Server配置
    """
    try:
        logger.info(f"收到更新MCP Server配置请求: id={config_id}")
        
        db = get_database()
        encryption_service = EncryptionService()
        
        tenant_id = get_tenant_id(req)
        
        with db.get_session() as session:
            config = session.query(MCPServerConfig).filter(
                MCPServerConfig.id == config_id,
                MCPServerConfig.tenant_id == tenant_id
            ).first()
            
            if not config:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"MCP Server配置不存在: {config_id}"
                )
            
            # 更新字段
            if request.name is not None:
                config.name = request.name
            if request.url is not None:
                config.url = request.url
            if request.auth_type is not None:
                config.auth_type = request.auth_type
            if request.auth_token is not None:
                config.encrypted_auth_token = encryption_service.encrypt(request.auth_token)
            
            session.commit()
            session.refresh(config)
            
            response = MCPServerResponse(
                id=config.id,
                name=config.name,
                url=config.url,
                auth_type=config.auth_type,
                available_tools=[
                    MCPToolResponse(**tool)
                    for tool in json.loads(config.available_tools)
                ] if config.available_tools else None,
                created_at=to_iso_string(config.created_at),
                updated_at=to_iso_string(config.updated_at)
            )
        
        logger.info(f"MCP Server配置更新成功: id={config_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新MCP Server配置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新MCP Server配置失败: {str(e)}"
        )


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mcp_server_config(config_id: str, req: Request):
    """
    删除MCP Server配置
    """
    try:
        logger.info(f"收到删除MCP Server配置请求: id={config_id}")
        
        db = get_database()
        
        tenant_id = get_tenant_id(req)
        
        with db.get_session() as session:
            config = session.query(MCPServerConfig).filter(
                MCPServerConfig.id == config_id,
                MCPServerConfig.tenant_id == tenant_id
            ).first()
            
            if not config:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"MCP Server配置不存在: {config_id}"
                )
            
            session.delete(config)
            session.commit()
        
        logger.info(f"MCP Server配置删除成功: id={config_id}")
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除MCP Server配置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除MCP Server配置失败: {str(e)}"
        )


@router.post("/{config_id}/test", response_model=ConnectionTestResponse, status_code=status.HTTP_200_OK)
async def test_mcp_server_connection(config_id: str):
    """
    测试MCP Server连接
    """
    try:
        logger.info(f"收到测试MCP Server连接请求: id={config_id}")
        
        db = get_database()
        mcp_connector = MCPConnector(db)
        
        # 测试连接
        result = await mcp_connector.test_connection(config_id)
        
        response = ConnectionTestResponse(
            success=result.success,
            message=result.message,
            error=result.error
        )
        
        logger.info(f"MCP Server连接测试完成: id={config_id}, success={result.success}")
        return response
        
    except Exception as e:
        logger.error(f"测试MCP Server连接失败: {str(e)}", exc_info=True)
        return ConnectionTestResponse(
            success=False,
            message="连接测试失败",
            error=str(e)
        )


@router.get("/{config_id}/tools", response_model=List[MCPToolResponse], status_code=status.HTTP_200_OK)
async def get_mcp_server_tools(config_id: str):
    """
    获取MCP Server可用工具列表
    """
    try:
        logger.info(f"收到获取MCP Server工具列表请求: id={config_id}")
        
        db = get_database()
        mcp_connector = MCPConnector(db)
        
        # 获取工具列表
        tools = await mcp_connector.get_available_tools(config_id)
        
        response = [
            MCPToolResponse(
                name=tool.name,
                description=tool.description,
                parameters=tool.parameters
            )
            for tool in tools
        ]
        
        logger.info(f"返回MCP Server工具列表: id={config_id}, count={len(response)}")
        return response
        
    except Exception as e:
        logger.error(f"获取MCP Server工具列表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取MCP Server工具列表失败: {str(e)}"
        )
