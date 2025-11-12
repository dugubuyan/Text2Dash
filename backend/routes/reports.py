"""
报表生成相关API路由
"""
import json
import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ..services.report_service import get_report_service, ReportResult
from ..database import get_database
from ..models.saved_report import SavedReport
from ..utils.logger import get_logger
from ..utils.datetime_helper import to_iso_string

logger = get_logger(__name__)
router = APIRouter(prefix="/api/reports", tags=["reports"])


# ============ Request/Response Models ============

class QueryRequest(BaseModel):
    """自然语言查询请求"""
    query: str = Field(..., description="用户的自然语言查询")
    model: str = Field(default="gemini/gemini-2.0-flash", description="使用的LLM模型")
    session_id: Optional[str] = Field(None, description="会话ID，如果不提供则创建新会话")
    data_source_ids: List[str] = Field(..., description="数据源ID列表（数据库和MCP Server）")


class SaveReportRequest(BaseModel):
    """保存常用报表请求"""
    name: str = Field(..., description="报表名称")
    description: Optional[str] = Field(None, description="报表描述")
    query_plan: dict = Field(..., description="查询计划（JSON）")
    chart_config: Optional[dict] = Field(None, description="图表配置（JSON），text类型时可为None")
    summary: Optional[str] = Field(None, description="第一次生成的summary")
    original_query: Optional[str] = Field(None, description="原始查询")
    data_source_ids: List[str] = Field(..., description="数据源ID列表")


class UpdateReportRequest(BaseModel):
    """更新常用报表请求"""
    name: Optional[str] = Field(None, description="报表名称")
    description: Optional[str] = Field(None, description="报表描述")


class RunSavedReportRequest(BaseModel):
    """执行常用报表请求"""
    with_analysis: bool = Field(default=False, description="是否需要LLM分析")
    session_id: Optional[str] = Field(None, description="会话ID")
    model: Optional[str] = Field(None, description="使用的LLM模型（仅在with_analysis=True时需要）")


class ReportResponse(BaseModel):
    """报表响应"""
    session_id: str
    interaction_id: str
    sql_query: Optional[str]
    query_plan: Optional[dict]
    chart_config: Optional[dict]  # text 类型时可以为 None
    summary: str
    data: List[dict]
    metadata: dict
    original_query: str
    data_source_ids: List[str]
    model: str = Field(default="gemini/gemini-2.0-flash", description="使用的LLM模型")


class SavedReportResponse(BaseModel):
    """常用报表响应"""
    id: str
    name: str
    description: Optional[str]
    query_plan: dict
    chart_config: Optional[dict]  # text 类型时可以为 None
    summary: Optional[str]
    original_query: Optional[str]
    data_source_ids: List[str]
    created_at: str
    updated_at: str


# ============ API Endpoints ============

@router.post("/query", response_model=ReportResponse, status_code=status.HTTP_200_OK)
async def generate_report(request: QueryRequest):
    """
    自然语言查询生成报表
    
    完整流程：
    1. 获取会话上下文
    2. 调用LLM生成查询计划
    3. 执行查询并组合数据
    4. 应用敏感信息过滤
    5. 生成图表配置和总结
    """
    try:
        logger.info(f"收到报表生成请求: query='{request.query[:50]}...', model={request.model}")
        
        # 如果没有提供session_id，创建新会话
        if not request.session_id:
            from ..services.session_manager import SessionManager
            from ..database import get_database
            
            session_manager = SessionManager(get_database())
            request.session_id = await session_manager.create_session(user_id=None)
            logger.info(f"创建新会话: session_id={request.session_id}")
        
        # 获取报表服务并生成报表
        report_service = get_report_service()
        result = await report_service.generate_report(
            query=request.query,
            model=request.model,
            session_id=request.session_id,
            data_source_ids=request.data_source_ids
        )
        
        # 构建响应
        # 将 QueryPlan 对象转换为字典
        query_plan_dict = None
        if hasattr(result, 'query_plan') and result.query_plan:
            if hasattr(result.query_plan, 'model_dump'):
                query_plan_dict = result.query_plan.model_dump()
            elif hasattr(result.query_plan, 'dict'):
                query_plan_dict = result.query_plan.dict()
        
        response = ReportResponse(
            session_id=result.session_id,
            interaction_id=result.interaction_id,
            sql_query=result.sql_query,
            query_plan=query_plan_dict,
            chart_config=result.chart_config,
            summary=result.summary,
            data=result.data,
            metadata={
                "columns": result.metadata.columns,
                "column_types": result.metadata.column_types,
                "row_count": result.metadata.row_count
            },
            original_query=request.query,
            data_source_ids=request.data_source_ids
        )
        
        logger.info(f"报表生成成功: interaction_id={result.interaction_id}")
        return response
        
    except Exception as e:
        logger.error(f"报表生成失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"报表生成失败: {str(e)}"
        )


@router.post("/saved", response_model=SavedReportResponse, status_code=status.HTTP_201_CREATED)
async def save_report(request: SaveReportRequest):
    """
    保存常用报表
    """
    try:
        logger.info(f"收到保存报表请求: name={request.name}")
        
        db = get_database()
        
        # 创建新的常用报表
        report_id = str(uuid.uuid4())
        saved_report = SavedReport(
            id=report_id,
            name=request.name,
            description=request.description,
            query_plan=json.dumps(request.query_plan, ensure_ascii=False),
            chart_config=json.dumps(request.chart_config, ensure_ascii=False),
            summary=request.summary,
            original_query=request.original_query,
            data_source_ids=json.dumps(request.data_source_ids, ensure_ascii=False)
        )
        
        with db.get_session() as session:
            session.add(saved_report)
            session.commit()
            session.refresh(saved_report)
            
            response = SavedReportResponse(
                id=saved_report.id,
                name=saved_report.name,
                description=saved_report.description,
                query_plan=json.loads(saved_report.query_plan),
                chart_config=json.loads(saved_report.chart_config),
                summary=saved_report.summary,
                original_query=saved_report.original_query,
                data_source_ids=json.loads(saved_report.data_source_ids),
                created_at=to_iso_string(saved_report.created_at),
                updated_at=to_iso_string(saved_report.updated_at)
            )
        
        logger.info(f"报表保存成功: id={report_id}")
        return response
        
    except Exception as e:
        logger.error(f"保存报表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"保存报表失败: {str(e)}"
        )


@router.get("/saved", response_model=List[SavedReportResponse], status_code=status.HTTP_200_OK)
async def get_saved_reports():
    """
    获取常用报表列表
    """
    try:
        logger.info("收到获取报表列表请求")
        
        db = get_database()
        
        with db.get_session() as session:
            reports = session.query(SavedReport).order_by(SavedReport.created_at.desc()).all()
            
            response = [
                SavedReportResponse(
                    id=report.id,
                    name=report.name,
                    description=report.description,
                    query_plan=json.loads(report.query_plan),
                    chart_config=json.loads(report.chart_config),
                    summary=report.summary,
                    original_query=report.original_query,
                    data_source_ids=json.loads(report.data_source_ids),
                    created_at=to_iso_string(report.created_at),
                    updated_at=to_iso_string(report.updated_at)
                )
                for report in reports
            ]
        
        logger.info(f"返回报表列表: count={len(response)}")
        return response
        
    except Exception as e:
        logger.error(f"获取报表列表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取报表列表失败: {str(e)}"
        )


@router.get("/saved/{report_id}", response_model=SavedReportResponse, status_code=status.HTTP_200_OK)
async def get_saved_report(report_id: str):
    """
    获取单个常用报表
    """
    try:
        logger.info(f"收到获取报表请求: id={report_id}")
        
        db = get_database()
        
        with db.get_session() as session:
            report = session.query(SavedReport).filter(SavedReport.id == report_id).first()
            
            if not report:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"报表不存在: {report_id}"
                )
            
            response = SavedReportResponse(
                id=report.id,
                name=report.name,
                description=report.description,
                query_plan=json.loads(report.query_plan),
                chart_config=json.loads(report.chart_config),
                summary=report.summary,
                original_query=report.original_query,
                data_source_ids=json.loads(report.data_source_ids),
                created_at=to_iso_string(report.created_at),
                updated_at=to_iso_string(report.updated_at)
            )
        
        logger.info(f"返回报表: id={report_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取报表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取报表失败: {str(e)}"
        )


@router.put("/saved/{report_id}", response_model=SavedReportResponse, status_code=status.HTTP_200_OK)
async def update_saved_report(report_id: str, request: UpdateReportRequest):
    """
    更新常用报表
    """
    try:
        logger.info(f"收到更新报表请求: id={report_id}")
        
        db = get_database()
        
        with db.get_session() as session:
            report = session.query(SavedReport).filter(SavedReport.id == report_id).first()
            
            if not report:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"报表不存在: {report_id}"
                )
            
            # 更新字段
            if request.name is not None:
                report.name = request.name
            if request.description is not None:
                report.description = request.description
            
            session.commit()
            session.refresh(report)
            
            response = SavedReportResponse(
                id=report.id,
                name=report.name,
                description=report.description,
                query_plan=json.loads(report.query_plan),
                chart_config=json.loads(report.chart_config),
                summary=report.summary,
                original_query=report.original_query,
                data_source_ids=json.loads(report.data_source_ids),
                created_at=to_iso_string(report.created_at),
                updated_at=to_iso_string(report.updated_at)
            )
        
        logger.info(f"报表更新成功: id={report_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新报表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新报表失败: {str(e)}"
        )


@router.delete("/saved/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_report(report_id: str):
    """
    删除常用报表
    """
    try:
        logger.info(f"收到删除报表请求: id={report_id}")
        
        db = get_database()
        
        with db.get_session() as session:
            report = session.query(SavedReport).filter(SavedReport.id == report_id).first()
            
            if not report:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"报表不存在: {report_id}"
                )
            
            session.delete(report)
            session.commit()
        
        logger.info(f"报表删除成功: id={report_id}")
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除报表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除报表失败: {str(e)}"
        )


@router.post("/saved/{report_id}/run", response_model=ReportResponse, status_code=status.HTTP_200_OK)
async def run_saved_report(report_id: str, request: RunSavedReportRequest):
    """
    执行常用报表
    
    两种模式：
    - with_analysis=False: 直接执行查询+渲染（零LLM调用，最快）
    - with_analysis=True: 执行查询+调用LLM一次生成分析
    """
    try:
        logger.info(
            f"收到执行报表请求: id={report_id}, "
            f"with_analysis={request.with_analysis}"
        )
        
        # 如果需要分析但没有提供session_id，创建新会话
        if request.with_analysis and not request.session_id:
            from ..services.session_manager import SessionManager
            from ..database import get_database
            
            session_manager = SessionManager(get_database())
            request.session_id = await session_manager.create_session(user_id=None)
            logger.info(f"创建新会话: session_id={request.session_id}")
        
        # 获取报表服务并执行报表
        report_service = get_report_service()
        result = await report_service.run_saved_report(
            report_id=report_id,
            with_analysis=request.with_analysis,
            session_id=request.session_id,
            model=request.model
        )
        
        # 构建响应
        # 将 QueryPlan 对象转换为字典
        query_plan_dict = None
        if hasattr(result, 'query_plan') and result.query_plan:
            if hasattr(result.query_plan, 'model_dump'):
                query_plan_dict = result.query_plan.model_dump()
            elif hasattr(result.query_plan, 'dict'):
                query_plan_dict = result.query_plan.dict()
            elif isinstance(result.query_plan, dict):
                query_plan_dict = result.query_plan
        
        response = ReportResponse(
            session_id=result.session_id,
            interaction_id=result.interaction_id,
            sql_query=result.sql_query,
            query_plan=query_plan_dict,
            chart_config=result.chart_config,
            summary=result.summary,
            data=result.data,
            metadata={
                "columns": result.metadata.columns,
                "column_types": result.metadata.column_types,
                "row_count": result.metadata.row_count
            },
            original_query=result.original_query or "",
            data_source_ids=result.data_source_ids or []
        )
        
        logger.info(f"报表执行成功: report_id={report_id}")
        return response
        
    except Exception as e:
        logger.error(f"执行报表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"执行报表失败: {str(e)}"
        )
