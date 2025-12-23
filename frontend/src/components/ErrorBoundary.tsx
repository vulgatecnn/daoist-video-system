import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
}

/**
 * 错误边界组件
 * 捕获子组件中的JavaScript错误并显示友好的错误界面
 */
class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    // 更新state以显示错误UI
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // 记录错误信息
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    
    this.setState({
      error,
      errorInfo
    });

    // 发送错误报告到后端
    this.reportError(error, errorInfo);
  }

  private reportError = async (error: Error, errorInfo: ErrorInfo) => {
    try {
      const errorReport = {
        message: error.message,
        stack: error.stack,
        componentStack: errorInfo.componentStack,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        url: window.location.href,
        userId: localStorage.getItem('userId') || 'anonymous'
      };

      // 发送到后端错误收集API
      await fetch('/api/monitoring/client-error/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
        },
        body: JSON.stringify(errorReport)
      });
    } catch (reportError) {
      console.error('Failed to report error:', reportError);
    }
  };

  private handleReload = () => {
    window.location.reload();
  };

  private handleGoHome = () => {
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      // 如果提供了自定义fallback，使用它
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // 默认错误UI
      return (
        <div className="error-boundary">
          <div className="error-container">
            <div className="error-icon">⚠️</div>
            <h2 className="error-title">出现了一些问题</h2>
            <p className="error-message">
              抱歉，应用程序遇到了意外错误。我们已经记录了这个问题，技术团队会尽快修复。
            </p>
            
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details className="error-details">
                <summary>错误详情（开发模式）</summary>
                <pre className="error-stack">
                  {this.state.error.message}
                  {'\n\n'}
                  {this.state.error.stack}
                  {this.state.errorInfo?.componentStack && (
                    <>
                      {'\n\n组件堆栈:'}
                      {this.state.errorInfo.componentStack}
                    </>
                  )}
                </pre>
              </details>
            )}

            <div className="error-actions">
              <button 
                onClick={this.handleReload}
                className="btn btn-primary"
              >
                重新加载页面
              </button>
              <button 
                onClick={this.handleGoHome}
                className="btn btn-secondary"
              >
                返回首页
              </button>
            </div>
          </div>

          <style>{`
            .error-boundary {
              min-height: 100vh;
              display: flex;
              align-items: center;
              justify-content: center;
              background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
              padding: 20px;
            }

            .error-container {
              background: white;
              border-radius: 10px;
              box-shadow: 0 10px 30px rgba(0,0,0,0.2);
              padding: 40px;
              text-align: center;
              max-width: 600px;
              width: 100%;
            }

            .error-icon {
              font-size: 64px;
              margin-bottom: 20px;
            }

            .error-title {
              font-size: 24px;
              color: #2c3e50;
              margin-bottom: 15px;
              font-weight: 600;
            }

            .error-message {
              font-size: 16px;
              color: #7f8c8d;
              margin-bottom: 30px;
              line-height: 1.6;
            }

            .error-details {
              text-align: left;
              margin: 20px 0;
              padding: 15px;
              background: #f8f9fa;
              border-radius: 5px;
              border: 1px solid #e9ecef;
            }

            .error-details summary {
              cursor: pointer;
              font-weight: 600;
              color: #495057;
              margin-bottom: 10px;
            }

            .error-stack {
              background: #f1f3f4;
              padding: 15px;
              border-radius: 4px;
              font-size: 12px;
              line-height: 1.4;
              overflow-x: auto;
              white-space: pre-wrap;
              word-break: break-word;
            }

            .error-actions {
              display: flex;
              gap: 15px;
              justify-content: center;
              flex-wrap: wrap;
            }

            .btn {
              padding: 12px 24px;
              border: none;
              border-radius: 5px;
              font-size: 14px;
              cursor: pointer;
              transition: all 0.3s ease;
              text-decoration: none;
              display: inline-block;
            }

            .btn-primary {
              background-color: #3498db;
              color: white;
            }

            .btn-primary:hover {
              background-color: #2980b9;
            }

            .btn-secondary {
              background-color: #95a5a6;
              color: white;
            }

            .btn-secondary:hover {
              background-color: #7f8c8d;
            }
          `}</style>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;