"""
会话管理器 - 使用mem0管理用户对话上下文
"""
import os
import json
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime

# 可选导入mem0，如果不存在则禁用功能
try:
    from mem0 import Memory
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False
    Memory = None

from backend.utils.logger import get_logger
from backend.utils.datetime_helper import to_iso_string
from backend.database import Database
from backend.models.session import Session, SessionInteraction, ReportSnapshot
from .dto import ConversationMessage

logger = get_logger(__name__)


class SessionManager:
    """会话管理器类 - 管理用户会话和对话上下文"""
    
    def __init__(self, database: Database, use_mem0: bool = None):
        """
        初始化会话管理器
        
        Args:
            database: 数据库实例
            use_mem0: 是否使用mem0（默认从环境变量读取，如果未设置则为False）
        """
        self.db = database
        self.context_threshold = int(os.getenv("SESSION_CONTEXT_THRESHOLD", "10"))
        
        # 如果没有显式传入use_mem0参数，从环境变量读取
        if use_mem0 is None:
            use_mem0_env = os.getenv("USE_MEM0", "false").lower()
            self.use_mem0 = use_mem0_env in ("true", "1", "yes")
        else:
            self.use_mem0 = use_mem0
        self.memory = None
        
        if self.use_mem0:
            if not MEM0_AVAILABLE:
                logger.warning("Mem0依赖未安装，禁用Mem0功能")
                self.use_mem0 = False
                self.memory = None
                return
                
            try:
                # 确保向量存储目录存在
                vector_store_path = os.getenv("MEM0_VECTOR_STORE_PATH", "./data/mem0_vector_store")
                os.makedirs(vector_store_path, exist_ok=True)
                
                # 配置本地mem0，使用HuggingFace嵌入模型
                config = {
                    "embedder": {
                        "provider": "huggingface",
                        "config": {
                            "model": "sentence-transformers/all-MiniLM-L12-v2"
                        }
                    },
                    "vector_store": {
                        "provider": "qdrant",
                        "config": {
                            "collection_name": "session_memories",
                            "embedding_model_dims": 384,  # all-MiniLM-L12-v2的维度
                            "path": vector_store_path
                        }
                    }
                }
                
                # 只有在配置了API密钥时才添加LLM配置
                if os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY"):
                    config["llm"] = {
                        "provider": "litellm",
                        "config": {
                            "model": os.getenv("DEFAULT_MODEL", "gemini/gemini-2.0-flash-exp"),
                            "temperature": 0.3,
                            "max_tokens": 2000
                        }
                    }
                
                self.memory = Memory.from_config(config)
                logger.info("Mem0客户端初始化完成（本地模式，使用HuggingFace嵌入模型）")
            except Exception as e:
                logger.warning(f"Mem0初始化失败，将仅使用数据库存储: {e}")
                self.use_mem0 = False
                self.memory = None
        else:
            logger.info("Mem0功能已禁用，仅使用数据库存储")
        
        logger.info(f"会话管理器初始化完成，上下文阈值: {self.context_threshold}")
    
    async def create_session(self, user_id: str = None, tenant_id: int = 0) -> str:
        """
        创建新会话
        
        Args:
            user_id: 用户ID（可选）
            tenant_id: 租户ID（可选，默认为0）
        
        Returns:
            会话ID
        """
        session_id = str(uuid.uuid4())
        
        try:
            with self.db.get_session() as db_session:
                # 创建会话记录
                session = Session(
                    id=session_id,
                    tenant_id=tenant_id,  # Set tenant_id
                    user_id=user_id,
                    created_at=datetime.utcnow(),
                    last_activity=datetime.utcnow()
                )
                db_session.add(session)
                db_session.commit()
            
            logger.info(f"创建新会话: session_id={session_id}, user_id={user_id}")
            
            return session_id
            
        except Exception as e:
            logger.error(f"创建会话失败: {e}", exc_info=True)
            raise Exception(f"创建会话失败: {str(e)}")
    
    async def get_context(self, session_id: str, limit: int = None) -> List[ConversationMessage]:
        """
        获取会话上下文
        
        Args:
            session_id: 会话ID
            limit: 返回的消息数量限制（可选）
        
        Returns:
            会话消息列表
        """
        try:
            # 从数据库获取会话交互历史
            interactions_data = []
            with self.db.get_session() as db_session:
                # 验证会话是否存在
                session = db_session.query(Session).filter(
                    Session.id == session_id
                ).first()
                
                if not session:
                    logger.warning(f"会话不存在: session_id={session_id}")
                    return []
                
                # 获取交互历史
                query = db_session.query(SessionInteraction).filter(
                    SessionInteraction.session_id == session_id
                ).order_by(SessionInteraction.created_at.asc())
                
                if limit:
                    query = query.limit(limit)
                
                interactions = query.all()
                
                # 在会话内提取所有数据
                for interaction in interactions:
                    interactions_data.append({
                        'user_query': interaction.user_query,
                        'summary': interaction.summary,
                        'created_at': interaction.created_at
                    })
            
            # 转换为ConversationMessage列表
            messages = []
            for data in interactions_data:
                # 用户查询
                messages.append(ConversationMessage(
                    role="user",
                    content=data['user_query'],
                    timestamp=data['created_at']
                ))
                
                # 助手响应（如果有总结）
                if data['summary']:
                    messages.append(ConversationMessage(
                        role="assistant",
                        content=data['summary'],
                        timestamp=data['created_at']
                    ))
            
            # 尝试从mem0获取记忆（如果启用）
            if self.use_mem0 and self.memory:
                try:
                    memories = self.memory.get_all(user_id=session_id)
                    if memories:
                        logger.debug(f"从mem0获取到 {len(memories)} 条记忆")
                except Exception as e:
                    logger.warning(f"从mem0获取记忆失败: {e}")
            
            logger.info(f"获取会话上下文: session_id={session_id}, messages={len(messages)}")
            
            return messages
            
        except Exception as e:
            logger.error(f"获取会话上下文失败: {e}", exc_info=True)
            raise Exception(f"获取会话上下文失败: {str(e)}")

    async def add_interaction(
        self,
        session_id: str,
        user_query: str,
        sql_query: str = None,
        chart_config: Dict[str, Any] = None,
        summary: str = None,
        data_snapshot: Any = None
    ) -> str:
        """
        添加交互记录到会话
        
        Args:
            session_id: 会话ID
            user_query: 用户查询
            sql_query: SQL查询语句（可选）
            chart_config: 图表配置（可选）
            summary: 报告总结（可选）
            data_snapshot: 数据快照（可选）
        
        Returns:
            交互ID
        """
        interaction_id = str(uuid.uuid4())
        return await self.add_interaction_with_id(
            interaction_id=interaction_id,
            session_id=session_id,
            user_query=user_query,
            sql_query=sql_query,
            chart_config=chart_config,
            summary=summary,
            data_snapshot=data_snapshot
        )
    
    async def add_interaction_with_id(
        self,
        interaction_id: str,
        session_id: str,
        user_query: str,
        sql_query: str = None,
        query_plan: Dict[str, Any] = None,
        chart_config: Dict[str, Any] = None,
        summary: str = None,
        data_source_ids: List[str] = None,
        data_snapshot: Any = None,
        temp_table_name: str = None
    ) -> str:
        """
        使用指定ID添加交互记录到会话
        
        Args:
            interaction_id: 交互ID
            session_id: 会话ID
            user_query: 用户查询
            sql_query: SQL查询语句（可选）
            query_plan: 查询计划（可选）
            chart_config: 图表配置（可选）
            summary: 报告总结（可选）
            data_source_ids: 数据源ID列表（可选）
            data_snapshot: 数据快照（可选）
            temp_table_name: 临时表名（可选）
        
        Returns:
            交互ID
        """
        
        try:
            with self.db.get_session() as db_session:
                # 验证会话是否存在
                session = db_session.query(Session).filter(
                    Session.id == session_id
                ).first()
                
                if not session:
                    raise Exception(f"会话不存在: {session_id}")
                
                # 创建交互记录
                interaction = SessionInteraction(
                    id=interaction_id,
                    session_id=session_id,
                    user_query=user_query,
                    sql_query=sql_query,
                    query_plan=json.dumps(query_plan) if query_plan else None,
                    chart_config=json.dumps(chart_config) if chart_config else None,
                    summary=summary,
                    data_source_ids=json.dumps(data_source_ids) if data_source_ids else None,
                    temp_table_name=temp_table_name,
                    created_at=datetime.utcnow()
                )
                db_session.add(interaction)
                
                # 如果有数据快照，创建快照记录
                if data_snapshot is not None:
                    snapshot = ReportSnapshot(
                        id=str(uuid.uuid4()),
                        session_id=session_id,
                        interaction_id=interaction_id,
                        data_snapshot=json.dumps(data_snapshot) if not isinstance(data_snapshot, str) else data_snapshot,
                        created_at=datetime.utcnow()
                    )
                    db_session.add(snapshot)
                
                # 更新会话的最后活动时间
                session.last_activity = datetime.utcnow()
                
                db_session.commit()
            
            # 将交互添加到mem0记忆（如果启用）
            if self.use_mem0 and self.memory:
                try:
                    # 构建记忆内容
                    memory_content = f"用户查询: {user_query}"
                    if summary:
                        memory_content += f"\n分析结果: {summary}"
                    
                    self.memory.add(
                        messages=[{"role": "user", "content": memory_content}],
                        user_id=session_id
                    )
                    logger.debug(f"交互已添加到mem0记忆: interaction_id={interaction_id}")
                except Exception as e:
                    logger.warning(f"添加到mem0记忆失败: {e}")
            
            logger.info(
                f"添加会话交互: session_id={session_id}, "
                f"interaction_id={interaction_id}, "
                f"has_sql={sql_query is not None}, "
                f"has_chart={chart_config is not None}, "
                f"temp_table={temp_table_name}"
            )
            
            return interaction_id
            
        except Exception as e:
            logger.error(f"添加会话交互失败: {e}", exc_info=True)
            raise Exception(f"添加会话交互失败: {str(e)}")
    
    async def check_and_compress(
        self,
        session_id: str,
        llm_service
    ) -> bool:
        """
        检查上下文长度，必要时压缩
        
        Args:
            session_id: 会话ID
            llm_service: LLM服务实例（用于生成摘要）
        
        Returns:
            是否执行了压缩
        """
        try:
            # 获取当前会话的所有消息
            messages = await self.get_context(session_id)
            
            # 检查是否超过阈值
            if len(messages) <= self.context_threshold:
                logger.debug(
                    f"会话上下文未超过阈值: session_id={session_id}, "
                    f"messages={len(messages)}, threshold={self.context_threshold}"
                )
                return False
            
            logger.info(
                f"会话上下文超过阈值，开始压缩: session_id={session_id}, "
                f"messages={len(messages)}, threshold={self.context_threshold}"
            )
            
            # 调用LLM压缩会话历史
            summary = await llm_service.summarize_conversation(messages)
            
            # 将摘要存储到mem0（如果启用）
            if self.use_mem0 and self.memory:
                try:
                    self.memory.add(
                        messages=[{
                            "role": "system",
                            "content": f"会话摘要（压缩自{len(messages)}条消息）: {summary}"
                        }],
                        user_id=session_id
                    )
                    logger.info(f"会话摘要已存储到mem0: session_id={session_id}")
                except Exception as e:
                    logger.warning(f"存储摘要到mem0失败: {e}")
            
            # 可选：在数据库中标记旧的交互为已压缩
            # 这里我们保留原始数据，只是添加了摘要
            
            logger.info(f"会话压缩完成: session_id={session_id}, summary_length={len(summary)}")
            
            return True
            
        except Exception as e:
            logger.error(f"检查和压缩会话失败: {e}", exc_info=True)
            # 压缩失败不应该阻止主流程，只记录错误
            return False
    
    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话信息
        
        Args:
            session_id: 会话ID
        
        Returns:
            会话信息字典，如果会话不存在则返回None
        """
        try:
            with self.db.get_session() as db_session:
                session = db_session.query(Session).filter(
                    Session.id == session_id
                ).first()
                
                if not session:
                    return None
                
                # 获取交互数量
                interaction_count = db_session.query(SessionInteraction).filter(
                    SessionInteraction.session_id == session_id
                ).count()
                
                return {
                    "id": session.id,
                    "user_id": session.user_id,
                    "created_at": to_iso_string(session.created_at),
                    "last_activity": to_iso_string(session.last_activity),
                    "interaction_count": interaction_count
                }
                
        except Exception as e:
            logger.error(f"获取会话信息失败: {e}", exc_info=True)
            return None
    
    async def get_session_history(
        self,
        session_id: str,
        limit: int = None,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取会话历史记录
        
        Args:
            session_id: 会话ID
            limit: 返回的记录数量限制（可选）
            offset: 偏移量（用于分页）
        
        Returns:
            交互记录列表
        """
        try:
            with self.db.get_session() as db_session:
                query = db_session.query(SessionInteraction).filter(
                    SessionInteraction.session_id == session_id
                ).order_by(SessionInteraction.created_at.desc())
                
                if offset:
                    query = query.offset(offset)
                
                if limit:
                    query = query.limit(limit)
                
                interactions = query.all()
                
                # 转换为字典列表
                history = []
                for interaction in interactions:
                    history.append({
                        "id": interaction.id,
                        "session_id": interaction.session_id,
                        "user_query": interaction.user_query,
                        "sql_query": interaction.sql_query,
                        "chart_config": json.loads(interaction.chart_config) if interaction.chart_config else None,
                        "summary": interaction.summary,
                        "created_at": to_iso_string(interaction.created_at)
                    })
                
                logger.info(
                    f"获取会话历史: session_id={session_id}, "
                    f"count={len(history)}, limit={limit}, offset={offset}"
                )
                
                return history
                
        except Exception as e:
            logger.error(f"获取会话历史失败: {e}", exc_info=True)
            raise Exception(f"获取会话历史失败: {str(e)}")
    
    async def get_last_interaction(
        self,
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取最后一次交互
        
        Args:
            session_id: 会话ID
        
        Returns:
            交互信息字典，如果没有交互则返回None
        """
        try:
            with self.db.get_session() as db_session:
                interaction = db_session.query(SessionInteraction).filter(
                    SessionInteraction.session_id == session_id
                ).order_by(SessionInteraction.created_at.desc()).first()
                
                if not interaction:
                    return None
                
                return {
                    "id": interaction.id,
                    "user_query": interaction.user_query,
                    "summary": interaction.summary,
                    "temp_table_name": interaction.temp_table_name,
                    "query_plan": json.loads(interaction.query_plan) if interaction.query_plan else None,
                    "chart_config": json.loads(interaction.chart_config) if interaction.chart_config else None,
                    "data_source_ids": json.loads(interaction.data_source_ids) if interaction.data_source_ids else None
                }
                
        except Exception as e:
            logger.error(f"获取最后交互失败: {e}", exc_info=True)
            return None
    
    async def get_all_interactions(
        self,
        session_id: str
    ) -> List[Dict[str, Any]]:
        """
        获取会话的所有交互历史
        
        Args:
            session_id: 会话ID
        
        Returns:
            交互信息列表，按时间升序排列
        """
        try:
            with self.db.get_session() as db_session:
                interactions = db_session.query(SessionInteraction).filter(
                    SessionInteraction.session_id == session_id
                ).order_by(SessionInteraction.created_at.asc()).all()
                
                result = []
                for interaction in interactions:
                    result.append({
                        "id": interaction.id,
                        "user_query": interaction.user_query,
                        "summary": interaction.summary,
                        "temp_table_name": interaction.temp_table_name,
                        "chart_config": json.loads(interaction.chart_config) if interaction.chart_config else None,
                        "data_source_ids": json.loads(interaction.data_source_ids) if interaction.data_source_ids else None,
                        "created_at": interaction.created_at.isoformat() if interaction.created_at else None
                    })
                
                return result
                
        except Exception as e:
            logger.error(f"获取所有交互失败: {e}", exc_info=True)
            return []
    
    async def delete_session(self, session_id: str) -> bool:
        """
        删除会话及其所有相关数据
        
        Args:
            session_id: 会话ID
        
        Returns:
            是否删除成功
        """
        try:
            with self.db.get_session() as db_session:
                # 删除报表快照
                db_session.query(ReportSnapshot).filter(
                    ReportSnapshot.session_id == session_id
                ).delete()
                
                # 删除交互记录
                db_session.query(SessionInteraction).filter(
                    SessionInteraction.session_id == session_id
                ).delete()
                
                # 删除会话
                deleted = db_session.query(Session).filter(
                    Session.id == session_id
                ).delete()
                
                db_session.commit()
            
            # 尝试从mem0删除记忆（如果启用）
            if self.use_mem0 and self.memory:
                try:
                    self.memory.delete_all(user_id=session_id)
                    logger.debug(f"已从mem0删除会话记忆: session_id={session_id}")
                except Exception as e:
                    logger.warning(f"从mem0删除记忆失败: {e}")
            
            logger.info(f"删除会话: session_id={session_id}, success={deleted > 0}")
            
            return deleted > 0
            
        except Exception as e:
            logger.error(f"删除会话失败: {e}", exc_info=True)
            raise Exception(f"删除会话失败: {str(e)}")
