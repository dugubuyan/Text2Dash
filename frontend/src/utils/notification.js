import { message, notification } from 'antd';

/**
 * Notification utility for consistent message handling
 */

// Message duration in seconds
const MESSAGE_DURATION = 3;
const NOTIFICATION_DURATION = 4.5;

/**
 * Show success message
 * @param {string} content - Message content
 */
export const showSuccess = (content) => {
  message.success(content, MESSAGE_DURATION);
};

/**
 * Show error message
 * @param {string} content - Message content
 */
export const showError = (content) => {
  message.error(content, MESSAGE_DURATION);
};

/**
 * Show warning message
 * @param {string} content - Message content
 */
export const showWarning = (content) => {
  message.warning(content, MESSAGE_DURATION);
};

/**
 * Show info message
 * @param {string} content - Message content
 */
export const showInfo = (content) => {
  message.info(content, MESSAGE_DURATION);
};

/**
 * Show loading message
 * @param {string} content - Message content
 * @returns {function} - Function to close the loading message
 */
export const showLoading = (content = '加载中...') => {
  return message.loading(content, 0);
};

/**
 * Show success notification with title and description
 * @param {string} title - Notification title
 * @param {string} description - Notification description
 */
export const notifySuccess = (title, description) => {
  notification.success({
    message: title,
    description,
    duration: NOTIFICATION_DURATION,
    placement: 'topRight',
  });
};

/**
 * Show error notification with title and description
 * @param {string} title - Notification title
 * @param {string} description - Notification description
 */
export const notifyError = (title, description) => {
  notification.error({
    message: title,
    description,
    duration: NOTIFICATION_DURATION,
    placement: 'topRight',
  });
};

/**
 * Show warning notification with title and description
 * @param {string} title - Notification title
 * @param {string} description - Notification description
 */
export const notifyWarning = (title, description) => {
  notification.warning({
    message: title,
    description,
    duration: NOTIFICATION_DURATION,
    placement: 'topRight',
  });
};

/**
 * Show info notification with title and description
 * @param {string} title - Notification title
 * @param {string} description - Notification description
 */
export const notifyInfo = (title, description) => {
  notification.info({
    message: title,
    description,
    duration: NOTIFICATION_DURATION,
    placement: 'topRight',
  });
};

/**
 * Handle API error and show appropriate notification
 * @param {Error} error - Error object from API call
 * @param {string} defaultMessage - Default message if error details not available
 */
export const handleApiError = (error, defaultMessage = '操作失败') => {
  if (error.response) {
    const { status, data } = error.response;
    const errorMessage = data.detail || data.message || defaultMessage;
    
    switch (status) {
      case 400:
        notifyError('请求错误', errorMessage);
        break;
      case 401:
        notifyError('未授权', '请重新登录');
        break;
      case 403:
        notifyError('禁止访问', '您没有权限执行此操作');
        break;
      case 404:
        notifyError('未找到', '请求的资源不存在');
        break;
      case 500:
        notifyError('服务器错误', '服务器内部错误，请稍后重试');
        break;
      default:
        notifyError('错误', errorMessage);
    }
  } else if (error.request) {
    notifyError('网络错误', '无法连接到服务器，请检查网络连接');
  } else {
    notifyError('错误', error.message || defaultMessage);
  }
};

/**
 * Show success notification for common operations
 */
export const operationSuccess = {
  create: (itemName = '项目') => showSuccess(`${itemName}创建成功`),
  update: (itemName = '项目') => showSuccess(`${itemName}更新成功`),
  delete: (itemName = '项目') => showSuccess(`${itemName}删除成功`),
  save: (itemName = '项目') => showSuccess(`${itemName}保存成功`),
  export: (format = '文件') => showSuccess(`${format}导出成功`),
  test: (itemName = '连接') => showSuccess(`${itemName}测试成功`),
};

/**
 * Show error notification for common operations
 */
export const operationError = {
  create: (itemName = '项目') => showError(`${itemName}创建失败`),
  update: (itemName = '项目') => showError(`${itemName}更新失败`),
  delete: (itemName = '项目') => showError(`${itemName}删除失败`),
  save: (itemName = '项目') => showError(`${itemName}保存失败`),
  export: (format = '文件') => showError(`${format}导出失败`),
  test: (itemName = '连接') => showError(`${itemName}测试失败`),
  load: (itemName = '数据') => showError(`${itemName}加载失败`),
};

export default {
  showSuccess,
  showError,
  showWarning,
  showInfo,
  showLoading,
  notifySuccess,
  notifyError,
  notifyWarning,
  notifyInfo,
  handleApiError,
  operationSuccess,
  operationError,
};
