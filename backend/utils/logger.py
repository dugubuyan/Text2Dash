"""
日志配置模块
提供统一的日志记录功能，支持详细的错误日志记录
"""
import logging
import os
import sys
import traceback
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path


class DetailedFormatter(logging.Formatter):
    """详细的日志格式化器，包含额外的上下文信息"""
    
    def format(self, record: logging.LogRecord) -> str:
        """
        格式化日志记录
        
        Args:
            record: 日志记录对象
            
        Returns:
            格式化后的日志字符串
        """
        # 基础格式化
        formatted = super().format(record)
        
        # 如果有异常信息，添加详细的堆栈跟踪
        if record.exc_info:
            formatted += f"\n异常详情:\n{self.formatException(record.exc_info)}"
        
        # 如果有额外的上下文信息，添加到日志中
        if hasattr(record, 'extra_context'):
            formatted += f"\n上下文信息: {record.extra_context}"
        
        return formatted


def setup_logger(
    name: str = "business_report_generator",
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    console_output: bool = True
) -> logging.Logger:
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称
        log_level: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        log_file: 日志文件路径，如果为None则从环境变量读取
        console_output: 是否输出到控制台
        
    Returns:
        配置好的日志记录器
    """
    # 从环境变量获取配置
    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO")
    
    if log_file is None:
        log_file = os.getenv("LOG_FILE", "./logs/app.log")
    
    # 确保日志目录存在
    log_dir = os.path.dirname(log_file)
    if log_dir:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # 清除已有的处理器（避免重复添加）
    logger.handlers.clear()
    
    # 日志格式
    log_format = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # 文件处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(DetailedFormatter(log_format, date_format))
    logger.addHandler(file_handler)
    
    # 控制台处理器
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(DetailedFormatter(log_format, date_format))
        logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str = "business_report_generator") -> logging.Logger:
    """
    获取日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        日志记录器实例
    """
    logger = logging.getLogger(name)
    
    # 如果日志记录器还没有处理器，进行初始化
    if not logger.handlers:
        setup_logger(name)
    
    return logger


def log_error_with_context(
    logger: logging.Logger,
    message: str,
    error: Exception,
    context: Optional[Dict[str, Any]] = None
):
    """
    记录带有详细上下文的错误日志
    
    Args:
        logger: 日志记录器
        message: 错误消息
        error: 异常对象
        context: 额外的上下文信息（如SQL语句、参数等）
    """
    # 构建详细的错误信息
    error_details = {
        "message": message,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    # 添加上下文信息
    if context:
        error_details["context"] = context
    
    # 添加堆栈跟踪
    error_details["traceback"] = traceback.format_exc()
    
    # 记录错误
    logger.error(
        f"{message}\n详细信息: {error_details}",
        exc_info=True,
        extra={"extra_context": context}
    )


def log_sql_error(
    logger: logging.Logger,
    sql: str,
    db_config_id: str,
    error: Exception,
    parameters: Optional[Dict[str, Any]] = None
):
    """
    记录SQL执行错误
    
    Args:
        logger: 日志记录器
        sql: SQL语句
        db_config_id: 数据库配置ID
        error: 异常对象
        parameters: SQL参数
    """
    context = {
        "sql": sql,
        "db_config_id": db_config_id,
        "parameters": parameters,
    }
    log_error_with_context(logger, "SQL执行失败", error, context)


def log_llm_error(
    logger: logging.Logger,
    model: str,
    prompt: str,
    error: Exception,
    api_endpoint: Optional[str] = None
):
    """
    记录LLM服务调用错误
    
    Args:
        logger: 日志记录器
        model: 模型名称
        prompt: 提示词
        error: 异常对象
        api_endpoint: API端点
    """
    context = {
        "model": model,
        "prompt": prompt[:500] if prompt else None,  # 限制长度
        "api_endpoint": api_endpoint,
    }
    log_error_with_context(logger, "LLM服务调用失败", error, context)


def log_database_connection_error(
    logger: logging.Logger,
    db_config: Dict[str, Any],
    error: Exception
):
    """
    记录数据库连接错误
    
    Args:
        logger: 日志记录器
        db_config: 数据库配置（密码会被脱敏）
        error: 异常对象
    """
    # 脱敏处理
    safe_config = db_config.copy()
    if "password" in safe_config:
        safe_config["password"] = "***"
    if "encrypted_password" in safe_config:
        safe_config["encrypted_password"] = "***"
    
    context = {
        "db_config": safe_config,
    }
    log_error_with_context(logger, "数据库连接失败", error, context)


def log_mcp_error(
    logger: logging.Logger,
    mcp_config_id: str,
    tool_name: str,
    parameters: Dict[str, Any],
    error: Exception
):
    """
    记录MCP Server调用错误
    
    Args:
        logger: 日志记录器
        mcp_config_id: MCP Server配置ID
        tool_name: 工具名称
        parameters: 调用参数
        error: 异常对象
    """
    context = {
        "mcp_config_id": mcp_config_id,
        "tool_name": tool_name,
        "parameters": parameters,
    }
    log_error_with_context(logger, "MCP Server调用失败", error, context)


# 全局日志记录器
_global_logger = None


def get_global_logger() -> logging.Logger:
    """获取全局日志记录器"""
    global _global_logger
    if _global_logger is None:
        _global_logger = setup_logger()
    return _global_logger


if __name__ == "__main__":
    # 测试日志配置
    logger = setup_logger("test_logger", log_level="DEBUG")
    
    logger.debug("这是一条调试消息")
    logger.info("这是一条信息消息")
    logger.warning("这是一条警告消息")
    logger.error("这是一条错误消息")
    
    # 测试带上下文的错误日志
    try:
        raise ValueError("测试错误")
    except Exception as e:
        log_error_with_context(
            logger,
            "测试错误记录",
            e,
            {"test_param": "test_value", "sql": "SELECT * FROM test"}
        )
    
    print(f"\n日志已写入到: {os.getenv('LOG_FILE', './logs/app.log')}")
