"""
模型管理API路由
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ..services.llm_service import LLMService
from ..utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/models", tags=["models"])


# ============ Response Models ============

class ModelResponse(BaseModel):
    """模型响应"""
    id: str = Field(..., description="模型ID")
    name: str = Field(..., description="模型名称")
    provider: str = Field(..., description="提供商")
    description: Optional[str] = Field(None, description="模型描述")


# ============ API Endpoints ============

@router.get("", response_model=List[ModelResponse], status_code=status.HTTP_200_OK)
async def get_available_models():
    """
    获取可用模型列表
    
    返回系统支持的所有LLM模型
    """
    try:
        logger.info("收到获取可用模型列表请求")
        
        # 定义支持的模型列表
        # 这些模型通过LiteLLM支持
        models = [
            ModelResponse(
                id="gemini/gemini-2.0-flash",
                name="Gemini 2.0 Flash",
                provider="Google",
                description="快速、高效的Gemini模型，适合大多数任务"
            ),
            ModelResponse(
                id="deepseek/deepseek-chat",
                name="DeepSeek Chat",
                provider="DeepSeek",
                description="DeepSeek的对话模型，性价比高"
            ),
        ]
        
        logger.info(f"返回可用模型列表: count={len(models)}")
        return models
        
    except Exception as e:
        logger.error(f"获取可用模型列表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取可用模型列表失败: {str(e)}"
        )
