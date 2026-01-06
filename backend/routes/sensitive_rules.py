"""
敏感信息规则API路由
"""
import json
import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Request  # Added Request
from pydantic import BaseModel, Field

from ..services.llm_service import LLMService
from ..database import get_database
from ..models.sensitive_rule import SensitiveRule
from ..utils.logger import get_logger
from ..utils.datetime_helper import to_iso_string
from ..utils.tenant_helpers import get_tenant_id  # Added tenant helper

logger = get_logger(__name__)
router = APIRouter(prefix="/api/sensitive-rules", tags=["sensitive-rules"])


# ============ Request/Response Models ============

class CreateSensitiveRuleRequest(BaseModel):
    """创建敏感信息规则请求"""
    db_config_id: Optional[str] = Field(None, description="数据库配置ID")
    name: str = Field(..., description="规则名称")
    description: Optional[str] = Field(None, description="规则描述")
    mode: str = Field(..., description="处理模式（filter或mask）")
    table_name: Optional[str] = Field(None, description="表名")
    columns: List[str] = Field(..., description="列名列表")
    pattern: Optional[str] = Field(None, description="匹配模式")


class UpdateSensitiveRuleRequest(BaseModel):
    """更新敏感信息规则请求"""
    db_config_id: Optional[str] = Field(None, description="数据库配置ID")
    name: Optional[str] = Field(None, description="规则名称")
    description: Optional[str] = Field(None, description="规则描述")
    mode: Optional[str] = Field(None, description="处理模式")
    table_name: Optional[str] = Field(None, description="表名")
    columns: Optional[List[str]] = Field(None, description="列名列表")
    pattern: Optional[str] = Field(None, description="匹配模式")


class ParseRuleRequest(BaseModel):
    """解析规则请求"""
    natural_language: str = Field(..., description="自然语言描述的规则")
    db_config_id: Optional[str] = Field(None, description="数据库配置ID，用于获取schema信息")
    model: str = Field(default="gemini/gemini-2.0-flash", description="使用的LLM模型")


class SensitiveRuleResponse(BaseModel):
    """敏感信息规则响应"""
    id: str
    db_config_id: Optional[str]
    name: str
    description: Optional[str]
    mode: str
    table_name: Optional[str]
    columns: List[str]
    pattern: Optional[str]
    created_at: str
    updated_at: str


class ParsedRuleResponse(BaseModel):
    """解析后的规则响应"""
    name: str
    mode: str
    table_name: Optional[str]
    columns: List[str]
    pattern: Optional[str]


# ============ API Endpoints ============

@router.post("", response_model=SensitiveRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_sensitive_rule(request: CreateSensitiveRuleRequest, req: Request):
    """
    创建敏感信息规则
    """
    try:
        logger.info(f"收到创建敏感信息规则请求: name={request.name}, mode={request.mode}")
        
        db = get_database()
        
        tenant_id = get_tenant_id(req)
        
        # 创建敏感信息规则
        rule_id = str(uuid.uuid4())
        rule = SensitiveRule(
            id=rule_id,
            tenant_id=tenant_id,  # Set tenant_id
            db_config_id=request.db_config_id,
            name=request.name,
            description=request.description,
            mode=request.mode,
            table_name=request.table_name,
            columns=json.dumps(request.columns, ensure_ascii=False),
            pattern=request.pattern
        )
        
        with db.get_session() as session:
            session.add(rule)
            session.commit()
            session.refresh(rule)
            
            response = SensitiveRuleResponse(
                id=rule.id,
                db_config_id=rule.db_config_id,
                name=rule.name,
                description=rule.description,
                mode=rule.mode,
                table_name=rule.table_name,
                columns=json.loads(rule.columns),
                pattern=rule.pattern,
                created_at=to_iso_string(rule.created_at),
                updated_at=to_iso_string(rule.updated_at)
            )
        
        logger.info(f"敏感信息规则创建成功: id={rule_id}")
        return response
        
    except Exception as e:
        logger.error(f"创建敏感信息规则失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建敏感信息规则失败: {str(e)}"
        )


@router.get("", response_model=List[SensitiveRuleResponse], status_code=status.HTTP_200_OK)
async def get_sensitive_rules(req: Request, db_config_id: Optional[str] = None):
    """
    获取所有敏感信息规则
    
    Args:
        db_config_id: 可选的数据库配置ID，用于过滤规则
    """
    try:
        logger.info(f"收到获取敏感信息规则列表请求: db_config_id={db_config_id}")
        
        db = get_database()
        
        tenant_id = get_tenant_id(req)
        
        with db.get_session() as session:
            query = session.query(SensitiveRule).filter(
                SensitiveRule.tenant_id == tenant_id
            )
            
            if db_config_id:
                query = query.filter(SensitiveRule.db_config_id == db_config_id)
            
            rules = query.order_by(SensitiveRule.created_at.desc()).all()
            
            response = [
                SensitiveRuleResponse(
                    id=rule.id,
                    db_config_id=rule.db_config_id,
                    name=rule.name,
                    description=rule.description,
                    mode=rule.mode,
                    table_name=rule.table_name,
                    columns=json.loads(rule.columns),
                    pattern=rule.pattern,
                    created_at=to_iso_string(rule.created_at),
                    updated_at=to_iso_string(rule.updated_at)
                )
                for rule in rules
            ]
        
        logger.info(f"返回敏感信息规则列表: count={len(response)}")
        return response
        
    except Exception as e:
        logger.error(f"获取敏感信息规则列表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取敏感信息规则列表失败: {str(e)}"
        )


@router.put("/{rule_id}", response_model=SensitiveRuleResponse, status_code=status.HTTP_200_OK)
async def update_sensitive_rule(rule_id: str, request: UpdateSensitiveRuleRequest, req: Request):
    """
    更新敏感信息规则
    """
    try:
        logger.info(f"收到更新敏感信息规则请求: id={rule_id}")
        
        db = get_database()
        
        tenant_id = get_tenant_id(req)
        
        with db.get_session() as session:
            rule = session.query(SensitiveRule).filter(
                SensitiveRule.id == rule_id,
                SensitiveRule.tenant_id == tenant_id
            ).first()
            
            if not rule:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"敏感信息规则不存在: {rule_id}"
                )
            
            # 更新字段
            if request.db_config_id is not None:
                rule.db_config_id = request.db_config_id
            if request.name is not None:
                rule.name = request.name
            if request.description is not None:
                rule.description = request.description
            if request.mode is not None:
                rule.mode = request.mode
            if request.table_name is not None:
                rule.table_name = request.table_name
            if request.columns is not None:
                rule.columns = json.dumps(request.columns, ensure_ascii=False)
            if request.pattern is not None:
                rule.pattern = request.pattern
            
            session.commit()
            session.refresh(rule)
            
            response = SensitiveRuleResponse(
                id=rule.id,
                db_config_id=rule.db_config_id,
                name=rule.name,
                description=rule.description,
                mode=rule.mode,
                table_name=rule.table_name,
                columns=json.loads(rule.columns),
                pattern=rule.pattern,
                created_at=to_iso_string(rule.created_at),
                updated_at=to_iso_string(rule.updated_at)
            )
        
        logger.info(f"敏感信息规则更新成功: id={rule_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新敏感信息规则失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新敏感信息规则失败: {str(e)}"
        )


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sensitive_rule(rule_id: str, req: Request):
    """
    删除敏感信息规则
    """
    try:
        logger.info(f"收到删除敏感信息规则请求: id={rule_id}")
        
        db = get_database()
        
        tenant_id = get_tenant_id(req)
        
        with db.get_session() as session:
            rule = session.query(SensitiveRule).filter(
                SensitiveRule.id == rule_id,
                SensitiveRule.tenant_id == tenant_id
            ).first()
            
            if not rule:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"敏感信息规则不存在: {rule_id}"
                )
            
            session.delete(rule)
            session.commit()
        
        logger.info(f"敏感信息规则删除成功: id={rule_id}")
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除敏感信息规则失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除敏感信息规则失败: {str(e)}"
        )


@router.post("/parse", response_model=List[ParsedRuleResponse], status_code=status.HTTP_200_OK)
async def parse_sensitive_rule(request: ParseRuleRequest):
    """
    自然语言解析规则
    
    将自然语言描述转换为结构化的敏感信息规则（可能返回多个规则）
    """
    try:
        logger.info(f"收到解析敏感信息规则请求: text='{request.natural_language[:50]}...', db_config_id={request.db_config_id}")
        
        # 获取数据库schema信息（如果提供了db_config_id）
        db_schema_info = None
        if request.db_config_id:
            from ..services.database_connector import get_database_connector
            db_connector = get_database_connector()
            db_schema_info = await db_connector.get_schema_info(request.db_config_id)
            logger.info(f"获取数据库schema信息: db_config_id={request.db_config_id}")
        
        llm_service = LLMService()
        
        # 调用LLM解析规则（现在返回列表）
        parsed_rules = await llm_service.parse_sensitive_rule(
            natural_language=request.natural_language,
            db_schema_info=db_schema_info,
            model=request.model
        )
        
        response = [
            ParsedRuleResponse(
                name=rule.name,
                mode=rule.mode,
                table_name=rule.table_name,
                columns=rule.columns,
                pattern=rule.pattern
            )
            for rule in parsed_rules
        ]
        
        logger.info(f"敏感信息规则解析成功: count={len(response)}")
        return response
        
    except Exception as e:
        logger.error(f"解析敏感信息规则失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"解析敏感信息规则失败: {str(e)}"
        )
