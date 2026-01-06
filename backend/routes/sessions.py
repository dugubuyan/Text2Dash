"""
会话管理API路由
"""
import json
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Request  # Added Request
from pydantic import BaseModel, Field

from ..services.session_manager import SessionManager
from ..database import get_database
from ..models.session import Session, SessionInteraction, ReportSnapshot
from ..utils.logger import get_logger
from ..utils.datetime_helper import to_iso_string
from ..utils.tenant_helpers import get_tenant_id  # Added tenant helper

logger = get_logger(__name__)
router = APIRouter(prefix="/api/sessions", tags=["sessions"])


# ============ Request/Response Models ============

class CreateSessionRequest(BaseModel):
    """创建会话请求"""
    user_id: Optional[str] = Field(None, description="用户ID")


class SessionResponse(BaseModel):
    """会话响应"""
    id: str
    user_id: Optional[str]
    created_at: str
    last_activity: str


class InteractionResponse(BaseModel):
    """交互响应"""
    id: str
    session_id: str
    user_query: str
    sql_query: Optional[str]
    query_plan: Optional[dict]
    chart_config: Optional[dict]
    summary: Optional[str]
    data_source_ids: Optional[List[str]]
    data_snapshot: Optional[List[dict]] = None
    created_at: str


class SessionHistoryResponse(BaseModel):
    """会话历史响应"""
    session: SessionResponse
    interactions: List[InteractionResponse]


# ============ API Endpoints ============

@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(request: CreateSessionRequest, req: Request):
    """
    创建新会话
    """
    try:
        logger.info(f"收到创建会话请求: user_id={request.user_id}")
        
        db = get_database()
        session_manager = SessionManager(db)
        
        # 创建新会话
        tenant_id = get_tenant_id(req)
        session_id = await session_manager.create_session(user_id=request.user_id, tenant_id=tenant_id)
        
        # 获取会话信息
        with db.get_session() as db_session:
            session = db_session.query(Session).filter(Session.id == session_id).first()
            
            if not session:
                raise Exception("会话创建失败")
            
            response = SessionResponse(
                id=session.id,
                user_id=session.user_id,
                created_at=to_iso_string(session.created_at),
                last_activity=to_iso_string(session.last_activity)
            )
        
        logger.info(f"会话创建成功: id={session_id}")
        return response
        
    except Exception as e:
        logger.error(f"创建会话失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建会话失败: {str(e)}"
        )


@router.get("/{session_id}", response_model=SessionResponse, status_code=status.HTTP_200_OK)
async def get_session(session_id: str, req: Request):
    """
    获取会话详情
    """
    try:
        logger.info(f"收到获取会话请求: id={session_id}")
        
        db = get_database()
        
        tenant_id = get_tenant_id(req)
        
        with db.get_session() as db_session:
            session = db_session.query(Session).filter(
                Session.id == session_id,
                Session.tenant_id == tenant_id
            ).first()
            
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"会话不存在: {session_id}"
                )
            
            response = SessionResponse(
                id=session.id,
                user_id=session.user_id,
                created_at=to_iso_string(session.created_at),
                last_activity=to_iso_string(session.last_activity)
            )
        
        logger.info(f"返回会话: id={session_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取会话失败: {str(e)}"
        )


@router.get("/{session_id}/history", response_model=SessionHistoryResponse, status_code=status.HTTP_200_OK)
async def get_session_history(session_id: str, req: Request, limit: Optional[int] = None):
    """
    获取会话历史
    
    Args:
        session_id: 会话ID
        limit: 限制返回的交互数量（可选）
    """
    try:
        logger.info(f"收到获取会话历史请求: id={session_id}, limit={limit}")
        
        db = get_database()
        
        with db.get_session() as db_session:
            # 获取会话信息
            tenant_id = get_tenant_id(req)
            session = db_session.query(Session).filter(
                Session.id == session_id,
                Session.tenant_id == tenant_id
            ).first()
            
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"会话不存在: {session_id}"
                )
            
            # 获取交互历史
            query = db_session.query(SessionInteraction).filter(
                SessionInteraction.session_id == session_id
            ).order_by(SessionInteraction.created_at.desc())
            
            if limit:
                query = query.limit(limit)
            
            interactions = query.all()
            
            # 构建响应
            session_response = SessionResponse(
                id=session.id,
                user_id=session.user_id,
                created_at=to_iso_string(session.created_at),
                last_activity=to_iso_string(session.last_activity)
            )
            
            # 为每个交互加载数据快照
            interactions_response = []
            for interaction in interactions:
                # 查询对应的数据快照
                snapshot = db_session.query(ReportSnapshot).filter(
                    ReportSnapshot.interaction_id == interaction.id
                ).first()
                
                # 解析数据快照
                data_snapshot = None
                if snapshot and snapshot.data_snapshot:
                    try:
                        data_snapshot = json.loads(snapshot.data_snapshot)
                    except json.JSONDecodeError:
                        logger.warning(f"无法解析数据快照: interaction_id={interaction.id}")
                
                interactions_response.append(
                    InteractionResponse(
                        id=interaction.id,
                        session_id=interaction.session_id,
                        user_query=interaction.user_query,
                        sql_query=interaction.sql_query,
                        query_plan=json.loads(interaction.query_plan) if interaction.query_plan else None,
                        chart_config=json.loads(interaction.chart_config) if interaction.chart_config else None,
                        summary=interaction.summary,
                        data_source_ids=json.loads(interaction.data_source_ids) if interaction.data_source_ids else None,
                        data_snapshot=data_snapshot,
                        created_at=to_iso_string(interaction.created_at)
                    )
                )
            
            response = SessionHistoryResponse(
                session=session_response,
                interactions=interactions_response
            )
        
        logger.info(f"返回会话历史: id={session_id}, interactions={len(interactions_response)}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话历史失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取会话历史失败: {str(e)}"
        )
