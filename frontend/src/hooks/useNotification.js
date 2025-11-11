import { useCallback } from 'react';
import {
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
} from '../utils/notification';

/**
 * Custom hook for using notifications
 * Provides a convenient way to show notifications in components
 */
const useNotification = () => {
  const success = useCallback((content) => {
    showSuccess(content);
  }, []);

  const error = useCallback((content) => {
    showError(content);
  }, []);

  const warning = useCallback((content) => {
    showWarning(content);
  }, []);

  const info = useCallback((content) => {
    showInfo(content);
  }, []);

  const loading = useCallback((content) => {
    return showLoading(content);
  }, []);

  const notify = useCallback({
    success: (title, description) => notifySuccess(title, description),
    error: (title, description) => notifyError(title, description),
    warning: (title, description) => notifyWarning(title, description),
    info: (title, description) => notifyInfo(title, description),
  }, []);

  const handleError = useCallback((err, defaultMessage) => {
    handleApiError(err, defaultMessage);
  }, []);

  return {
    success,
    error,
    warning,
    info,
    loading,
    notify,
    handleError,
    operationSuccess,
    operationError,
  };
};

export default useNotification;
