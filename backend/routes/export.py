"""
导出API路由
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

from ..services.export_service import ExportService, ReportData
from ..utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/export", tags=["export"])


# ============ Request Models ============

class ExportRequest(BaseModel):
    """导出请求"""
    title: str = Field(..., description="报表标题")
    summary: str = Field(..., description="报表总结")
    chart_config: Optional[dict] = Field(None, description="图表配置")
    chart_image: Optional[str] = Field(None, description="图表图片(base64)")
    data: List[dict] = Field(..., description="数据")
    metadata: dict = Field(..., description="元数据")
    sql_query: Optional[str] = Field(None, description="SQL查询")


# ============ API Endpoints ============

@router.post("/pdf")
async def export_to_pdf(request: ExportRequest):
    """
    导出PDF
    
    生成包含图表和数据的PDF文件
    """
    try:
        logger.info(f"收到导出PDF请求: title={request.title}")
        
        from ..services.dto import DataMetadata
        from urllib.parse import quote
        
        export_service = ExportService()
        
        # 将字典转换为DataMetadata对象
        metadata = DataMetadata(
            columns=request.metadata.get('columns', []),
            column_types=request.metadata.get('column_types', {}),
            row_count=request.metadata.get('row_count', len(request.data))
        )
        
        # 处理图表图片（如果有）
        chart_image_bytes = None
        if request.chart_image:
            import base64
            try:
                chart_image_bytes = base64.b64decode(request.chart_image)
                logger.debug(f"图表图片解码成功: size={len(chart_image_bytes)} bytes")
            except Exception as e:
                logger.warning(f"解码图表图片失败: {e}")
        
        # 构建报表数据
        report_data = ReportData(
            title=request.title,
            summary=request.summary,
            chart_config=request.chart_config,
            chart_image=chart_image_bytes,
            data=request.data,
            metadata=metadata,
            sql_query=request.sql_query
        )
        
        # 生成PDF
        pdf_bytes = await export_service.export_to_pdf(report_data)
        
        logger.info(f"PDF导出成功: title={request.title}, size={len(pdf_bytes)} bytes")
        
        # URL编码文件名以支持中文
        encoded_filename = quote(f"{request.title}.pdf")
        
        # 返回PDF文件
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )
        
    except Exception as e:
        logger.error(f"导出PDF失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出PDF失败: {str(e)}"
        )


@router.post("/excel")
async def export_to_excel(request: ExportRequest):
    """
    导出Excel
    
    生成包含原始数据的Excel文件
    """
    try:
        logger.info(f"收到导出Excel请求: title={request.title}")
        
        from ..services.dto import DataMetadata
        from urllib.parse import quote
        
        export_service = ExportService()
        
        # 将字典转换为DataMetadata对象
        metadata = DataMetadata(
            columns=request.metadata.get('columns', []),
            column_types=request.metadata.get('column_types', {}),
            row_count=request.metadata.get('row_count', len(request.data))
        )
        
        # 构建报表数据
        report_data = ReportData(
            title=request.title,
            summary=request.summary,
            chart_config=request.chart_config,
            data=request.data,
            metadata=metadata,
            sql_query=request.sql_query
        )
        
        # 生成Excel
        excel_bytes = await export_service.export_to_excel(report_data)
        
        logger.info(f"Excel导出成功: title={request.title}, size={len(excel_bytes)} bytes")
        
        # URL编码文件名以支持中文
        encoded_filename = quote(f"{request.title}.xlsx")
        
        # 返回Excel文件
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )
        
    except Exception as e:
        logger.error(f"导出Excel失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出Excel失败: {str(e)}"
        )
