/**
 * 日期时间格式化工具
 * 
 * 处理原则：
 * 1. 后端存储和传输使用 UTC 时间（ISO 8601 格式）
 * 2. 前端自动转换为用户本地时区
 * 3. 显示相对时间（刚刚、5分钟前等）或绝对时间
 */

/**
 * 格式化为相对时间（如：刚刚、5分钟前、2小时前）
 * @param {string|Date} timestamp - ISO 8601 时间戳或 Date 对象
 * @returns {string} 格式化后的相对时间
 */
export const formatRelativeTime = (timestamp) => {
  if (!timestamp) return '';
  
  // 确保转换为 Date 对象
  const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
  
  // 检查是否为有效日期
  if (isNaN(date.getTime())) {
    console.error('Invalid date:', timestamp);
    return '无效时间';
  }
  
  const now = new Date();
  const diff = now - date; // 毫秒差
  
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  const weeks = Math.floor(days / 7);
  const months = Math.floor(days / 30);
  const years = Math.floor(days / 365);
  
  // 未来时间
  if (diff < 0) {
    return '刚刚';
  }
  
  // 1分钟内
  if (seconds < 60) {
    return '刚刚';
  }
  
  // 1小时内
  if (minutes < 60) {
    return `${minutes}分钟前`;
  }
  
  // 24小时内
  if (hours < 24) {
    return `${hours}小时前`;
  }
  
  // 7天内
  if (days < 7) {
    return `${days}天前`;
  }
  
  // 30天内
  if (days < 30) {
    return `${weeks}周前`;
  }
  
  // 1年内
  if (days < 365) {
    return `${months}个月前`;
  }
  
  // 1年以上
  return `${years}年前`;
};

/**
 * 格式化为绝对时间（如：2024-11-03 14:30）
 * @param {string|Date} timestamp - ISO 8601 时间戳或 Date 对象
 * @param {object} options - 格式化选项
 * @returns {string} 格式化后的绝对时间
 */
export const formatAbsoluteTime = (timestamp, options = {}) => {
  if (!timestamp) return '';
  
  const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
  
  if (isNaN(date.getTime())) {
    console.error('Invalid date:', timestamp);
    return '无效时间';
  }
  
  const defaultOptions = {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    ...options
  };
  
  return date.toLocaleString('zh-CN', defaultOptions);
};

/**
 * 格式化为短日期（如：11-03 14:30）
 * @param {string|Date} timestamp - ISO 8601 时间戳或 Date 对象
 * @returns {string} 格式化后的短日期
 */
export const formatShortTime = (timestamp) => {
  if (!timestamp) return '';
  
  const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
  
  if (isNaN(date.getTime())) {
    return '无效时间';
  }
  
  const now = new Date();
  const isToday = date.toDateString() === now.toDateString();
  const isThisYear = date.getFullYear() === now.getFullYear();
  
  // 今天：只显示时间
  if (isToday) {
    return date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
  }
  
  // 今年：显示月-日 时:分
  if (isThisYear) {
    return date.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
  }
  
  // 其他年份：显示年-月-日 时:分
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  });
};

/**
 * 智能格式化时间（自动选择相对或绝对时间）
 * @param {string|Date} timestamp - ISO 8601 时间戳或 Date 对象
 * @param {number} relativeThreshold - 相对时间阈值（天），超过此值显示绝对时间
 * @returns {string} 格式化后的时间
 */
export const formatSmartTime = (timestamp, relativeThreshold = 7) => {
  if (!timestamp) return '';
  
  const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
  
  if (isNaN(date.getTime())) {
    return '无效时间';
  }
  
  const now = new Date();
  const diff = now - date;
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  
  // 在阈值内使用相对时间
  if (days < relativeThreshold) {
    return formatRelativeTime(timestamp);
  }
  
  // 超过阈值使用绝对时间
  return formatShortTime(timestamp);
};

/**
 * 调试：显示时间戳的详细信息
 * @param {string|Date} timestamp - ISO 8601 时间戳或 Date 对象
 */
export const debugTimestamp = (timestamp) => {
  const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
  
  console.group('时间戳调试信息');
  console.log('原始值:', timestamp);
  console.log('Date 对象:', date);
  console.log('UTC 时间:', date.toUTCString());
  console.log('本地时间:', date.toLocaleString('zh-CN'));
  console.log('ISO 8601:', date.toISOString());
  console.log('时间戳 (ms):', date.getTime());
  console.log('时区偏移 (分钟):', date.getTimezoneOffset());
  console.log('相对时间:', formatRelativeTime(timestamp));
  console.log('绝对时间:', formatAbsoluteTime(timestamp));
  console.log('短时间:', formatShortTime(timestamp));
  console.groupEnd();
};

export default {
  formatRelativeTime,
  formatAbsoluteTime,
  formatShortTime,
  formatSmartTime,
  debugTimestamp
};
