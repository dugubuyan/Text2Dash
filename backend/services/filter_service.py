"""
敏感信息过滤服务
"""
import json
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session as SQLAlchemySession

from ..database import Database
from ..models.sensitive_rule import SensitiveRule as SensitiveRuleModel
from ..utils.logger import get_logger

logger = get_logger(__name__)


class FilterService:
    """敏感信息过滤服务"""
    
    def __init__(self, database: Database):
        """
        初始化过滤服务
        
        Args:
            database: 数据库实例
        """
        self.database = database
    
    async def apply_filters(
        self,
        data: List[Dict[str, Any]],
        db_config_id: str
    ) -> List[Dict[str, Any]]:
        """
        应用敏感信息过滤规则
        
        Args:
            data: 原始数据列表
            db_config_id: 数据库配置ID
        
        Returns:
            过滤后的数据列表
        """
        if not data:
            return data
        
        try:
            # 获取该数据库的所有过滤规则
            with self.database.get_session() as session:
                rules = session.query(SensitiveRuleModel).filter(
                    SensitiveRuleModel.db_config_id == db_config_id
                ).all()
            
            if not rules:
                logger.info(f"No sensitive rules found for db_config_id: {db_config_id}")
                return data
            
            # 应用每个规则
            filtered_data = data
            for rule in rules:
                columns = json.loads(rule.columns)
                
                if rule.mode == 'filter':
                    # 完全移除列
                    for column in columns:
                        filtered_data = self.filter_column(filtered_data, column)
                    logger.info(f"Applied filter rule '{rule.name}' - removed columns: {columns}")
                
                elif rule.mode == 'mask':
                    # 脱敏处理
                    for column in columns:
                        filtered_data = self.mask_column(
                            filtered_data, 
                            column, 
                            pattern=rule.pattern
                        )
                    logger.info(f"Applied mask rule '{rule.name}' - masked columns: {columns}")
                
                else:
                    logger.warning(f"Unknown filter mode: {rule.mode} for rule '{rule.name}'")
            
            return filtered_data
        
        except Exception as e:
            logger.error(
                f"Error applying filters for db_config_id {db_config_id}",
                extra={
                    "error": str(e),
                    "db_config_id": db_config_id,
                    "data_row_count": len(data)
                },
                exc_info=True
            )
            # 发生错误时返回原始数据，避免数据丢失
            return data
    
    def filter_column(
        self,
        data: List[Dict[str, Any]],
        column: str
    ) -> List[Dict[str, Any]]:
        """
        完全移除指定列
        
        Args:
            data: 数据列表
            column: 要移除的列名
        
        Returns:
            移除列后的数据列表
        """
        if not data:
            return data
        
        filtered_data = []
        for row in data:
            # 创建新字典，排除指定列
            filtered_row = {k: v for k, v in row.items() if k != column}
            filtered_data.append(filtered_row)
        
        return filtered_data
    
    def mask_column(
        self,
        data: List[Dict[str, Any]],
        column: str,
        pattern: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        脱敏处理指定列
        
        Args:
            data: 数据列表
            column: 要脱敏的列名
            pattern: 可选的正则表达式模式，用于部分脱敏
        
        Returns:
            脱敏后的数据列表
        """
        if not data:
            return data
        
        masked_data = []
        for row in data:
            masked_row = row.copy()
            
            if column in masked_row and masked_row[column] is not None:
                original_value = str(masked_row[column])
                
                if pattern:
                    # 使用正则表达式进行部分脱敏
                    try:
                        masked_value = self._apply_pattern_mask(original_value, pattern)
                    except Exception as e:
                        logger.warning(
                            f"Failed to apply pattern mask, using full mask instead",
                            extra={
                                "column": column,
                                "pattern": pattern,
                                "error": str(e)
                            }
                        )
                        masked_value = self._full_mask(original_value)
                else:
                    # 完全脱敏
                    masked_value = self._full_mask(original_value)
                
                masked_row[column] = masked_value
            
            masked_data.append(masked_row)
        
        return masked_data
    
    def _full_mask(self, value: str) -> str:
        """
        完全脱敏，将所有字符替换为星号
        
        Args:
            value: 原始值
        
        Returns:
            脱敏后的值
        """
        if len(value) <= 2:
            return '*' * len(value)
        
        # 保留首尾字符，中间用星号替换
        return value[0] + '*' * (len(value) - 2) + value[-1]
    
    def _apply_pattern_mask(self, value: str, pattern: str) -> str:
        """
        根据正则表达式模式进行部分脱敏
        
        Args:
            value: 原始值
            pattern: 脱敏模式，支持：
                    - 预定义模式: "phone", "email", "id_card", "keep_first_N", "keep_last_N"
                    - JSON格式自定义规则: {"type": "custom", "keep_start": 3, "keep_end": 4, "mask_char": "*"}
                    - 正则表达式替换: {"type": "regex", "pattern": "\\d", "replacement": "*"}
        
        Returns:
            脱敏后的值
        """
        # 尝试解析JSON格式的自定义规则
        if pattern.startswith('{'):
            try:
                rule = json.loads(pattern)
                return self._apply_custom_rule(value, rule)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON pattern: {pattern}, using full mask")
                return self._full_mask(value)
        
        # 支持常见的预定义脱敏模式
        if pattern.startswith("keep_first_"):
            try:
                keep_count = int(pattern.split("_")[-1])
                if len(value) <= keep_count:
                    return value
                return value[:keep_count] + '*' * (len(value) - keep_count)
            except (ValueError, IndexError):
                return self._full_mask(value)
        
        elif pattern.startswith("keep_last_"):
            try:
                keep_count = int(pattern.split("_")[-1])
                if len(value) <= keep_count:
                    return value
                return '*' * (len(value) - keep_count) + value[-keep_count:]
            except (ValueError, IndexError):
                return self._full_mask(value)
        
        elif pattern == "phone":
            # 手机号脱敏：保留前3位和后4位
            if len(value) >= 7:
                return value[:3] + '*' * (len(value) - 7) + value[-4:]
            return self._full_mask(value)
        
        elif pattern == "email":
            # 邮箱脱敏：保留第一个字符和@后的域名
            if '@' in value:
                parts = value.split('@')
                if len(parts[0]) > 1:
                    masked_local = parts[0][0] + '*' * (len(parts[0]) - 1)
                else:
                    masked_local = parts[0]
                return f"{masked_local}@{parts[1]}"
            return self._full_mask(value)
        
        elif pattern == "id_card":
            # 身份证号脱敏：保留前6位和后4位
            if len(value) >= 10:
                return value[:6] + '*' * (len(value) - 10) + value[-4:]
            return self._full_mask(value)
        
        else:
            # 默认完全脱敏
            return self._full_mask(value)
    
    def _apply_custom_rule(self, value: str, rule: Dict[str, Any]) -> str:
        """
        应用自定义脱敏规则
        
        Args:
            value: 原始值
            rule: 自定义规则字典，支持以下类型：
                  - {"type": "custom", "keep_start": N, "keep_end": M, "mask_char": "*"}
                  - {"type": "regex", "pattern": "regex", "replacement": "X"}
                  - {"type": "range", "ranges": [[0, 3], [8, 12]], "mask_char": "*"}
        
        Returns:
            脱敏后的值
        """
        rule_type = rule.get("type", "custom")
        
        try:
            if rule_type == "custom":
                # 自定义保留开头和结尾
                keep_start = rule.get("keep_start", 0)
                keep_end = rule.get("keep_end", 0)
                mask_char = rule.get("mask_char", "*")
                
                if len(value) <= keep_start + keep_end:
                    return value
                
                start_part = value[:keep_start] if keep_start > 0 else ""
                end_part = value[-keep_end:] if keep_end > 0 else ""
                middle_length = len(value) - keep_start - keep_end
                
                return start_part + mask_char * middle_length + end_part
            
            elif rule_type == "regex":
                # 正则表达式替换
                pattern = rule.get("pattern", "")
                replacement = rule.get("replacement", "*")
                
                if not pattern:
                    return self._full_mask(value)
                
                return re.sub(pattern, replacement, value)
            
            elif rule_type == "range":
                # 指定范围脱敏
                ranges = rule.get("ranges", [])
                mask_char = rule.get("mask_char", "*")
                
                if not ranges:
                    return self._full_mask(value)
                
                result = list(value)
                for start, end in ranges:
                    for i in range(start, min(end, len(result))):
                        if 0 <= i < len(result):
                            result[i] = mask_char
                
                return ''.join(result)
            
            else:
                logger.warning(f"Unknown custom rule type: {rule_type}")
                return self._full_mask(value)
        
        except Exception as e:
            logger.error(
                f"Error applying custom rule",
                extra={
                    "rule": rule,
                    "error": str(e)
                },
                exc_info=True
            )
            return self._full_mask(value)
