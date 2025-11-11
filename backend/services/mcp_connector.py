"""
MCP连接器
管理MCP Server连接和工具调用
"""
import json
from typing import Dict, List, Any, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ..database import get_database
from ..models.mcp_server_config import MCPServerConfig
from .encryption_service import get_encryption_service
from .dto import DataMetadata
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ConnectionTestResult:
    """连接测试结果"""
    def __init__(self, success: bool, message: str, error: Optional[str] = None):
        self.success = success
        self.message = message
        self.error = error


class MCPTool:
    """MCP工具信息"""
    def __init__(self, name: str, description: str, parameters: Dict[str, Any]):
        self.name = name
        self.description = description
        self.parameters = parameters
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


class MCPResult:
    """MCP工具调用结果"""
    def __init__(
        self,
        tool_name: str,
        data: Any,
        metadata: Optional[DataMetadata] = None
    ):
        self.tool_name = tool_name
        self.data = data
        self.metadata = metadata


class MCPConnector:
    """MCP连接器类"""
    
    def __init__(self):
        """初始化MCP连接器"""
        self.connections: Dict[str, ClientSession] = {}
        self.encryption_service = get_encryption_service()
        self.config_db = get_database()
    
    def _get_mcp_config(self, mcp_config_id: str) -> MCPServerConfig:
        """
        从配置数据库获取MCP配置
        
        Args:
            mcp_config_id: MCP配置ID
            
        Returns:
            MCPServerConfig对象
            
        Raises:
            ValueError: 如果配置不存在
        """
        with self.config_db.get_session() as session:
            mcp_config = session.query(MCPServerConfig).filter_by(id=mcp_config_id).first()
            if not mcp_config:
                raise ValueError(f"MCP Server配置不存在: {mcp_config_id}")
            return mcp_config
    
    def _decrypt_auth_token(self, encrypted_token: Optional[str]) -> Optional[str]:
        """
        解密认证令牌
        
        Args:
            encrypted_token: 加密的令牌
            
        Returns:
            解密后的令牌，如果输入为None则返回None
        """
        if not encrypted_token:
            return None
        
        try:
            return self.encryption_service.decrypt(encrypted_token)
        except Exception as e:
            logger.error(f"解密MCP认证令牌失败: {e}")
            raise ValueError("无法解密MCP认证令牌")
    
    async def _get_or_create_connection(self, mcp_config_id: str) -> ClientSession:
        """
        获取或创建MCP连接
        
        Args:
            mcp_config_id: MCP配置ID
            
        Returns:
            MCP ClientSession对象
        """
        # 如果连接已存在，直接返回
        if mcp_config_id in self.connections:
            return self.connections[mcp_config_id]
        
        # 获取配置
        mcp_config = self._get_mcp_config(mcp_config_id)
        
        # 解密认证令牌
        auth_token = self._decrypt_auth_token(mcp_config.encrypted_auth_token)
        
        # 解析URL为服务器参数
        # 假设URL格式为: command arg1 arg2 ...
        # 例如: "uvx mcp-server-sqlite --db-path /path/to/db"
        url_parts = mcp_config.url.split()
        if not url_parts:
            raise ValueError(f"无效的MCP Server URL: {mcp_config.url}")
        
        command = url_parts[0]
        args = url_parts[1:] if len(url_parts) > 1 else []
        
        # 构建环境变量
        env = {}
        if auth_token and mcp_config.auth_type:
            if mcp_config.auth_type == "bearer":
                env["BEARER_TOKEN"] = auth_token
            elif mcp_config.auth_type == "api_key":
                env["API_KEY"] = auth_token
        
        # 创建服务器参数
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env if env else None
        )
        
        # 创建连接
        try:
            # 使用stdio_client创建连接
            read, write = await stdio_client(server_params)
            session = ClientSession(read, write)
            await session.initialize()
            
            # 缓存连接
            self.connections[mcp_config_id] = session
            logger.info(f"创建MCP连接: {mcp_config.name}")
            
            return session
        
        except Exception as e:
            logger.error(
                f"创建MCP连接失败",
                extra={
                    "mcp_config_id": mcp_config_id,
                    "name": mcp_config.name,
                    "error": str(e)
                }
            )
            raise
    
    async def call_tool(
        self,
        mcp_config_id: str,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> MCPResult:
        """
        调用MCP Server工具
        返回的数据必须是表格形式（list[dict]）
        
        Args:
            mcp_config_id: MCP配置ID
            tool_name: 工具名称
            parameters: 工具参数
            
        Returns:
            MCPResult对象，包含工具调用结果
            
        Raises:
            ValueError: 如果配置不存在或数据格式不正确
            Exception: 如果工具调用失败
        """
        try:
            session = await self._get_or_create_connection(mcp_config_id)
            
            # 调用工具
            result = await session.call_tool(tool_name, parameters)
            
            # 提取数据
            # MCP工具返回的结果通常在result.content中
            data = result.content if hasattr(result, 'content') else result
            
            # 验证数据格式
            if not self.validate_tool_response(data):
                raise ValueError(
                    f"MCP工具返回的数据格式不正确，必须是表格形式（list[dict]）: "
                    f"tool={tool_name}, type={type(data)}"
                )
            
            logger.info(
                f"MCP工具调用成功: mcp_config_id={mcp_config_id}, "
                f"tool={tool_name}, rows={len(data)}"
            )
            
            # 提取元信息
            metadata = self.get_tool_metadata(data)
            
            return MCPResult(
                tool_name=tool_name,
                data=data,
                metadata=metadata
            )
        
        except Exception as e:
            logger.error(
                f"MCP工具调用失败",
                extra={
                    "mcp_config_id": mcp_config_id,
                    "tool_name": tool_name,
                    "parameters": parameters,
                    "error": str(e)
                }
            )
            raise
    
    def validate_tool_response(self, response: Any) -> bool:
        """
        验证工具返回的数据格式
        必须是list[dict]，每个dict的键相同
        如果不是表格形式，返回False
        
        Args:
            response: 工具返回的数据
            
        Returns:
            True如果数据格式正确，False否则
        """
        # 检查是否为列表
        if not isinstance(response, list):
            logger.warning(f"MCP响应不是列表: type={type(response)}")
            return False
        
        # 空列表也是有效的表格
        if len(response) == 0:
            return True
        
        # 检查第一个元素是否为字典
        if not isinstance(response[0], dict):
            logger.warning(f"MCP响应列表元素不是字典: type={type(response[0])}")
            return False
        
        # 获取第一行的键
        first_keys = set(response[0].keys())
        
        # 检查所有行的键是否相同
        for i, row in enumerate(response[1:], start=1):
            if not isinstance(row, dict):
                logger.warning(f"MCP响应第{i}行不是字典: type={type(row)}")
                return False
            
            if set(row.keys()) != first_keys:
                logger.warning(
                    f"MCP响应第{i}行的键与第一行不同: "
                    f"expected={first_keys}, got={set(row.keys())}"
                )
                return False
        
        return True
    
    async def get_available_tools(self, mcp_config_id: str) -> List[MCPTool]:
        """
        获取MCP Server可用工具列表
        在配置时验证工具是否返回表格数据
        
        Args:
            mcp_config_id: MCP配置ID
            
        Returns:
            MCPTool对象列表
            
        Raises:
            ValueError: 如果配置不存在
            Exception: 如果获取工具列表失败
        """
        try:
            session = await self._get_or_create_connection(mcp_config_id)
            
            # 获取工具列表
            tools_response = await session.list_tools()
            
            # 转换为MCPTool对象
            tools = []
            for tool in tools_response.tools:
                mcp_tool = MCPTool(
                    name=tool.name,
                    description=tool.description if hasattr(tool, 'description') else "",
                    parameters=tool.inputSchema if hasattr(tool, 'inputSchema') else {}
                )
                tools.append(mcp_tool)
            
            logger.info(
                f"获取MCP工具列表成功: mcp_config_id={mcp_config_id}, "
                f"tools={len(tools)}"
            )
            
            return tools
        
        except Exception as e:
            logger.error(
                f"获取MCP工具列表失败",
                extra={
                    "mcp_config_id": mcp_config_id,
                    "error": str(e)
                }
            )
            raise
    
    async def test_connection(self, mcp_config: MCPServerConfig) -> ConnectionTestResult:
        """
        测试MCP Server连接
        验证工具列表和数据格式
        
        Args:
            mcp_config: MCP Server配置对象
            
        Returns:
            ConnectionTestResult对象，包含测试结果
        """
        session = None
        try:
            # 解密认证令牌
            auth_token = self._decrypt_auth_token(mcp_config.encrypted_auth_token)
            
            # 解析URL
            url_parts = mcp_config.url.split()
            if not url_parts:
                return ConnectionTestResult(
                    success=False,
                    message="连接失败",
                    error="无效的MCP Server URL"
                )
            
            command = url_parts[0]
            args = url_parts[1:] if len(url_parts) > 1 else []
            
            # 构建环境变量
            env = {}
            if auth_token and mcp_config.auth_type:
                if mcp_config.auth_type == "bearer":
                    env["BEARER_TOKEN"] = auth_token
                elif mcp_config.auth_type == "api_key":
                    env["API_KEY"] = auth_token
            
            # 创建服务器参数
            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=env if env else None
            )
            
            # 创建临时连接
            read, write = await stdio_client(server_params)
            session = ClientSession(read, write)
            await session.initialize()
            
            # 获取工具列表以验证连接
            tools_response = await session.list_tools()
            tool_count = len(tools_response.tools)
            
            logger.info(f"MCP连接测试成功: {mcp_config.name}, tools={tool_count}")
            
            return ConnectionTestResult(
                success=True,
                message=f"连接成功: {mcp_config.name} ({tool_count} 个工具)"
            )
        
        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"MCP连接测试失败",
                extra={
                    "mcp_config": mcp_config.name,
                    "url": mcp_config.url,
                    "error": error_msg
                }
            )
            return ConnectionTestResult(
                success=False,
                message="连接失败",
                error=error_msg
            )
        
        finally:
            # 关闭临时连接
            if session:
                try:
                    await session.close()
                except:
                    pass
    
    def get_tool_metadata(self, data: List[Dict[str, Any]]) -> DataMetadata:
        """
        提取MCP返回数据的元信息
        
        Args:
            data: MCP工具返回的表格数据
            
        Returns:
            DataMetadata对象，包含列名、列类型和行数
        """
        # 获取行数
        row_count = len(data)
        
        # 如果没有数据，返回空元信息
        if row_count == 0:
            return DataMetadata(
                columns=[],
                column_types={},
                row_count=0
            )
        
        # 获取列名（从第一行）
        columns = list(data[0].keys())
        
        # 推断列类型
        column_types = {}
        for col in columns:
            # 尝试从第一个非None值推断类型
            value = None
            for row in data:
                value = row.get(col)
                if value is not None:
                    break
            
            # 推断Python类型
            if value is None:
                column_types[col] = "NULL"
            elif isinstance(value, bool):
                column_types[col] = "BOOLEAN"
            elif isinstance(value, int):
                column_types[col] = "INTEGER"
            elif isinstance(value, float):
                column_types[col] = "FLOAT"
            elif isinstance(value, str):
                column_types[col] = "TEXT"
            else:
                column_types[col] = str(type(value).__name__)
        
        logger.info(
            f"提取MCP数据元信息: columns={len(columns)}, "
            f"row_count={row_count}"
        )
        
        return DataMetadata(
            columns=columns,
            column_types=column_types,
            row_count=row_count
        )
    
    async def close_connection(self, mcp_config_id: str):
        """
        关闭指定的MCP连接
        
        Args:
            mcp_config_id: MCP配置ID
        """
        if mcp_config_id in self.connections:
            try:
                await self.connections[mcp_config_id].close()
                del self.connections[mcp_config_id]
                logger.info(f"关闭MCP连接: {mcp_config_id}")
            except Exception as e:
                logger.error(f"关闭MCP连接失败: {e}")
    
    async def close_all_connections(self):
        """关闭所有MCP连接"""
        for mcp_config_id in list(self.connections.keys()):
            await self.close_connection(mcp_config_id)
        logger.info("关闭所有MCP连接")


# 全局MCP连接器实例
_mcp_connector = None


def get_mcp_connector() -> MCPConnector:
    """获取全局MCP连接器实例"""
    global _mcp_connector
    if _mcp_connector is None:
        _mcp_connector = MCPConnector()
    return _mcp_connector
