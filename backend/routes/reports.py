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
from ..models.session import SessionInteraction
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
            elif isinstance(result.query_plan, dict):
                # 如果已经是字典（例如从 ReuseDataExecutor 返回的）
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
            original_query=request.query,
            data_source_ids=request.data_source_ids
        )
        
        logger.info(f"报表生成成功: interaction_id={result.interaction_id}")
        logger.debug(f"返回的query_plan: {query_plan_dict}")
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
    
    如果查询计划包含会话临时表，会自动追溯到原始查询并重建完整的查询链
    """
    try:
        logger.info(f"收到保存报表请求: name={request.name}")
        
        db = get_database()
        
        # 检查 query_plan 中是否包含会话临时表查询
        query_plan = request.query_plan
        has_session_temp_table = False
        session_temp_tables = []
        
        if query_plan and "sql_queries" in query_plan:
            for sql_query in query_plan["sql_queries"]:
                if sql_query.get("db_config_id") == "__session__":
                    has_session_temp_table = True
                    # 从SQL中提取临时表名
                    sql = sql_query.get("sql", "")
                    # 简单的表名提取（假设格式为 session_{session_id}_interaction_{num}）
                    import re
                    # 修改正则表达式，支持更多字符（包括数字、字母、下划线、连字符）
                    table_matches = re.findall(r'session_[\w\-]+_interaction_\d+', sql, re.IGNORECASE)
                    session_temp_tables.extend(table_matches)
                    logger.debug(f"从SQL中提取临时表: sql={sql[:100]}, tables={table_matches}")
        
        # 如果包含会话临时表查询，尝试重建完整查询链
        if has_session_temp_table:
            logger.info(f"检测到会话临时表依赖，尝试重建查询链: tables={session_temp_tables}")
            logger.debug(f"原始查询计划: {json.dumps(query_plan, ensure_ascii=False)}")
            
            try:
                # 重建查询计划
                rebuilt_query_plan = await _rebuild_query_plan_from_temp_tables(
                    session_temp_tables=session_temp_tables,
                    original_query_plan=query_plan,
                    db=db
                )
                
                if rebuilt_query_plan:
                    logger.info("成功重建查询计划，使用原始数据源")
                    logger.debug(f"重建后的查询计划: {json.dumps(rebuilt_query_plan, ensure_ascii=False)}")
                    query_plan = rebuilt_query_plan
                else:
                    # 重建失败，返回错误
                    logger.warning("无法重建查询计划，返回错误提示")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="该报表依赖于会话临时数据，且无法自动转换为原始查询。请使用原始数据源重新查询后再保存。"
                    )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"重建查询计划失败: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"无法保存报表：{str(e)}"
                )
        
        # 创建新的常用报表
        report_id = str(uuid.uuid4())
        saved_report = SavedReport(
            id=report_id,
            name=request.name,
            description=request.description,
            query_plan=json.dumps(query_plan, ensure_ascii=False),
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


# ============ Helper Functions ============

async def _rebuild_query_plan_from_temp_tables(
    session_temp_tables: List[str],
    original_query_plan: dict,
    db
) -> Optional[dict]:
    """
    从会话临时表追溯到原始查询，重建完整的查询计划
    
    Args:
        session_temp_tables: 会话临时表名列表
        original_query_plan: 原始查询计划（包含临时表引用）
        db: 数据库实例
    
    Returns:
        重建后的查询计划（使用原始数据源），如果无法重建则返回None
    """
    try:
        logger.info(f"开始重建查询计划: temp_tables={session_temp_tables}, count={len(session_temp_tables)}")
        
        if not session_temp_tables:
            logger.warning("没有临时表需要重建")
            return None
        
        # 收集所有原始查询
        original_sql_queries = []
        all_data_source_ids = set()
        
        with db.get_session() as db_session:
            for table_name in session_temp_tables:
                logger.debug(f"处理临时表: {table_name}")
                # 从数据库查找生成该临时表的交互记录
                interaction = db_session.query(SessionInteraction).filter(
                    SessionInteraction.temp_table_name == table_name
                ).first()
                
                if not interaction:
                    logger.warning(f"找不到临时表对应的交互记录: {table_name}")
                    # 尝试查询所有临时表，看看数据库中有哪些
                    all_temp_tables = db_session.query(SessionInteraction.temp_table_name).filter(
                        SessionInteraction.temp_table_name.isnot(None)
                    ).all()
                    logger.debug(f"数据库中的所有临时表: {[t[0] for t in all_temp_tables]}")
                    return None
                
                # 解析该交互的查询计划
                if not interaction.query_plan:
                    logger.warning(f"交互记录没有查询计划: {table_name}")
                    return None
                
                interaction_query_plan = json.loads(interaction.query_plan)
                
                # 检查是否还有嵌套的临时表引用
                has_nested_temp_table = False
                if "sql_queries" in interaction_query_plan:
                    for sq in interaction_query_plan["sql_queries"]:
                        if sq.get("db_config_id") == "__session__":
                            has_nested_temp_table = True
                            break
                
                if has_nested_temp_table:
                    # 递归重建
                    logger.info(f"检测到嵌套临时表引用，递归重建: {table_name}")
                    import re
                    nested_tables = re.findall(
                        r'session_[a-f0-9_]+_interaction_\d+',
                        json.dumps(interaction_query_plan),
                        re.IGNORECASE
                    )
                    nested_plan = await _rebuild_query_plan_from_temp_tables(
                        session_temp_tables=nested_tables,
                        original_query_plan=interaction_query_plan,
                        db=db
                    )
                    if not nested_plan:
                        return None
                    interaction_query_plan = nested_plan
                
                # 收集SQL查询
                if "sql_queries" in interaction_query_plan:
                    original_sql_queries.extend(interaction_query_plan["sql_queries"])
                
                # 收集数据源ID
                if interaction.data_source_ids:
                    data_source_ids = json.loads(interaction.data_source_ids)
                    all_data_source_ids.update(data_source_ids)
        
        # 如果没有找到任何原始查询，返回None
        if not original_sql_queries:
            logger.warning("没有找到任何原始SQL查询")
            return None
        
        # 构建新的查询计划
        rebuilt_plan = {
            "no_data_source_match": False,
            "user_message": None,
            "sql_queries": original_sql_queries,
            "mcp_calls": original_query_plan.get("mcp_calls", []),
            "needs_combination": len(original_sql_queries) > 1 or len(original_query_plan.get("mcp_calls", [])) > 0,
            "combination_strategy": None  # 需要重新生成组合SQL
        }
        
        logger.info(
            f"查询计划重建成功: "
            f"sql_queries={len(rebuilt_plan['sql_queries'])}, "
            f"data_sources={list(all_data_source_ids)}"
        )
        
        return rebuilt_plan
        
    except Exception as e:
        logger.error(f"重建查询计划失败: {e}", exc_info=True)
        return None
