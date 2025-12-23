import { AxiosError } from 'axios';

export interface ErrorReport {
  message: string;
  stack?: string;
  componentStack?: string;
  timestamp: string;
  userAgent: string;
  url: string;
  userId: string;
  type: 'javascript' | 'api' | 'network';
  statusCode?: number;
  endpoint?: string;
}

export interface ApiError {
  error: boolean;
  message: string;
  details?: any;
  status_code?: number;
  field_errors?: Record<string, string[]>;
}

class ErrorService {
  private errorQueue: ErrorReport[] = [];
  private isReporting = false;

  /**
   * 处理API错误
   */
  handleApiError(error: AxiosError): ApiError {
    console.error('API Error:', error);

    // 记录错误
    this.reportError({
      message: error.message,
      stack: error.stack,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
      userId: localStorage.getItem('userId') || 'anonymous',
      type: 'api',
      statusCode: error.response?.status,
      endpoint: error.config?.url
    });

    // 解析错误响应
    if (error.response?.data) {
      const responseData = error.response.data as any;
      
      // 如果后端返回了标准错误格式
      if (responseData.error !== undefined) {
        return responseData as ApiError;
      }
      
      // 处理DRF标准错误格式
      if (responseData.detail) {
        return {
          error: true,
          message: responseData.detail,
          status_code: error.response.status
        };
      }
      
      // 处理字段验证错误
      if (typeof responseData === 'object' && !Array.isArray(responseData)) {
        return {
          error: true,
          message: '数据验证失败',
          field_errors: responseData,
          status_code: error.response.status
        };
      }
    }

    // 根据状态码返回通用错误信息
    const statusCode = error.response?.status || 0;
    let message = '请求失败，请稍后重试';

    switch (statusCode) {
      case 400:
        message = '请求参数错误';
        break;
      case 401:
        message = '未登录或登录已过期，请重新登录';
        break;
      case 403:
        message = '权限不足，无法执行此操作';
        break;
      case 404:
        message = '请求的资源不存在';
        break;
      case 429:
        message = '请求过于频繁，请稍后再试';
        break;
      case 500:
        message = '服务器内部错误，请稍后重试';
        break;
      case 502:
      case 503:
      case 504:
        message = '服务暂时不可用，请稍后重试';
        break;
      default:
        if (statusCode === 0) {
          message = '网络连接失败，请检查网络设置';
        }
    }

    return {
      error: true,
      message,
      status_code: statusCode
    };
  }

  /**
   * 处理JavaScript错误
   */
  handleJavaScriptError(error: Error, errorInfo?: any): void {
    console.error('JavaScript Error:', error, errorInfo);

    this.reportError({
      message: error.message,
      stack: error.stack,
      componentStack: errorInfo?.componentStack,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
      userId: localStorage.getItem('userId') || 'anonymous',
      type: 'javascript'
    });
  }

  /**
   * 处理网络错误
   */
  handleNetworkError(error: Error): void {
    console.error('Network Error:', error);

    this.reportError({
      message: error.message,
      stack: error.stack,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
      userId: localStorage.getItem('userId') || 'anonymous',
      type: 'network'
    });
  }

  /**
   * 报告错误到后端
   */
  private async reportError(errorReport: ErrorReport): Promise<void> {
    // 添加到队列
    this.errorQueue.push(errorReport);

    // 如果正在报告，直接返回
    if (this.isReporting) {
      return;
    }

    // 开始报告错误
    this.isReporting = true;

    try {
      while (this.errorQueue.length > 0) {
        const errors = this.errorQueue.splice(0, 10); // 批量发送，每次最多10个

        try {
          await fetch('/api/monitoring/client-errors/', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
            },
            body: JSON.stringify({ errors })
          });
        } catch (reportError) {
          console.error('Failed to report errors:', reportError);
          // 如果报告失败，将错误重新加入队列（但限制重试次数）
          errors.forEach(error => {
            if (!error.stack?.includes('retry_count')) {
              error.stack = (error.stack || '') + '\n[retry_count: 1]';
              this.errorQueue.push(error);
            }
          });
        }

        // 避免过于频繁的请求
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    } finally {
      this.isReporting = false;
    }
  }

  /**
   * 显示用户友好的错误消息
   */
  showErrorMessage(error: ApiError | string, duration: number = 5000): void {
    const message = typeof error === 'string' ? error : error.message;
    
    // 创建错误提示元素
    const errorElement = document.createElement('div');
    errorElement.className = 'error-toast';
    errorElement.innerHTML = `
      <div class="error-toast-content">
        <span class="error-toast-icon">⚠️</span>
        <span class="error-toast-message">${message}</span>
        <button class="error-toast-close" onclick="this.parentElement.parentElement.remove()">×</button>
      </div>
    `;

    // 添加样式
    const style = document.createElement('style');
    style.textContent = `
      .error-toast {
        position: fixed;
        top: 20px;
        right: 20px;
        background: #fff;
        border: 1px solid #f5c6cb;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        max-width: 400px;
        animation: slideIn 0.3s ease-out;
      }

      .error-toast-content {
        display: flex;
        align-items: center;
        padding: 12px 16px;
        gap: 8px;
      }

      .error-toast-icon {
        font-size: 18px;
        flex-shrink: 0;
      }

      .error-toast-message {
        flex: 1;
        color: #721c24;
        font-size: 14px;
        line-height: 1.4;
      }

      .error-toast-close {
        background: none;
        border: none;
        font-size: 18px;
        cursor: pointer;
        color: #721c24;
        padding: 0;
        width: 20px;
        height: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        transition: background-color 0.2s;
      }

      .error-toast-close:hover {
        background-color: #f5c6cb;
      }

      @keyframes slideIn {
        from {
          transform: translateX(100%);
          opacity: 0;
        }
        to {
          transform: translateX(0);
          opacity: 1;
        }
      }
    `;

    // 添加到页面
    if (!document.querySelector('#error-toast-styles')) {
      style.id = 'error-toast-styles';
      document.head.appendChild(style);
    }

    document.body.appendChild(errorElement);

    // 自动移除
    setTimeout(() => {
      if (errorElement.parentNode) {
        errorElement.remove();
      }
    }, duration);
  }

  /**
   * 获取错误的用户友好描述
   */
  getErrorDescription(error: ApiError): string {
    if (error.field_errors) {
      const fieldErrors = Object.entries(error.field_errors)
        .map(([field, errors]) => `${field}: ${errors.join(', ')}`)
        .join('; ');
      return `${error.message}: ${fieldErrors}`;
    }

    return error.message;
  }

  /**
   * 检查是否为认证错误
   */
  isAuthError(error: ApiError): boolean {
    return error.status_code === 401;
  }

  /**
   * 检查是否为权限错误
   */
  isPermissionError(error: ApiError): boolean {
    return error.status_code === 403;
  }

  /**
   * 检查是否为网络错误
   */
  isNetworkError(error: ApiError): boolean {
    return error.status_code === 0 || !error.status_code;
  }
}

// 导出单例实例
export const errorService = new ErrorService();

// 设置全局错误处理
window.addEventListener('error', (event) => {
  errorService.handleJavaScriptError(event.error);
});

window.addEventListener('unhandledrejection', (event) => {
  errorService.handleJavaScriptError(new Error(event.reason));
});

export default errorService;