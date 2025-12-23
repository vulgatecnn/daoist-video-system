# API集成测试套件

## 项目结构

```
api_integration_tests/
├── __init__.py                 # 包初始化文件
├── conftest.py                 # pytest配置和夹具定义
├── README.md                   # 项目说明文档
├── config/                     # 配置模块
│   ├── __init__.py
│   └── test_config.py         # 测试配置管理器
├── utils/                      # 工具模块
│   ├── __init__.py
│   └── test_helpers.py        # 测试辅助工具
└── tests/                      # 测试用例目录
    ├── __init__.py
    ├── test_connection.py     # 连接性测试
    ├── test_auth.py           # 认证测试
    ├── test_videos.py         # 视频管理测试
    ├── test_composition.py    # 合成任务测试
    ├── test_monitoring.py     # 监控测试
    ├── test_errors.py         # 错误处理测试
    ├── test_performance.py    # 性能测试
    └── test_data_consistency.py  # 数据一致性测试
```

## 配置说明

### 环境变量

在运行测试前，可以通过环境变量配置测试参数：

- `BACKEND_URL`: 后端API地址（默认: http://localhost:6000）
- `FRONTEND_URL`: 前端地址（默认: http://localhost:5500）
- `API_TIMEOUT`: API请求超时时间（默认: 30秒）
- `API_RETRY_COUNT`: 重试次数（默认: 3次）
- `API_RETRY_DELAY`: 重试延迟（默认: 1.0秒）
- `TEST_USERNAME`: 测试用户名（默认: testuser）
- `TEST_PASSWORD`: 测试密码（默认: testpass123）
- `ADMIN_USERNAME`: 管理员用户名（默认: admin）
- `ADMIN_PASSWORD`: 管理员密码（默认: admin123）

### pytest配置

pytest配置文件位于 `backend/pytest.ini`，包含以下配置：

- 测试发现路径
- 输出格式配置
- 测试标记定义
- 日志配置
- 超时配置

## 运行测试

### 运行所有测试

```bash
cd backend
pytest api_integration_tests/
```

### 运行特定类型的测试

```bash
# 运行API测试
pytest -m api

# 运行集成测试
pytest -m integration

# 运行属性测试
pytest -m property

# 运行认证测试
pytest -m auth

# 运行性能测试
pytest -m performance
```

### 运行特定测试文件

```bash
pytest api_integration_tests/tests/test_auth.py
```

### 运行特定测试函数

```bash
pytest api_integration_tests/tests/test_auth.py::test_login_success
```

### 生成测试报告

```bash
# 生成HTML报告
pytest --html=report.html --self-contained-html

# 生成覆盖率报告
pytest --cov=api_integration_tests --cov-report=html
```

### 并行运行测试

```bash
# 使用所有CPU核心
pytest -n auto

# 使用指定数量的进程
pytest -n 4
```

## 测试标记

测试用例可以使用以下标记进行分类：

- `@pytest.mark.unit`: 单元测试
- `@pytest.mark.integration`: 集成测试
- `@pytest.mark.api`: API测试
- `@pytest.mark.auth`: 认证测试
- `@pytest.mark.video`: 视频相关测试
- `@pytest.mark.composition`: 合成任务测试
- `@pytest.mark.monitoring`: 监控测试
- `@pytest.mark.performance`: 性能测试
- `@pytest.mark.property`: 属性测试
- `@pytest.mark.slow`: 慢速测试
- `@pytest.mark.network`: 需要网络连接的测试

## 测试夹具

### 全局夹具

- `test_config`: 测试配置管理器
- `test_logger`: 测试日志记录器
- `api_endpoints`: API端点配置
- `test_data`: 测试数据
- `base_url`: API基础URL

### 函数级夹具

- `test_data_generator`: 测试数据生成器
- `test_file_manager`: 测试文件管理器

## 工具类

### TestConfigManager

配置管理器，提供测试环境的配置信息。

### TestDataGenerator

测试数据生成器，提供随机测试数据生成功能。

### TestFileManager

测试文件管理器，管理测试过程中创建的临时文件。

### ResponseValidator

响应验证器，验证API响应的格式和内容。

### TestLogger

测试日志记录器，记录测试过程中的日志信息。

### RetryHelper

重试辅助工具，提供带退避策略的重试功能。

## 开发指南

### 添加新的测试用例

1. 在 `tests/` 目录下创建新的测试文件
2. 导入必要的模块和夹具
3. 编写测试函数，使用 `test_` 前缀
4. 添加适当的测试标记
5. 使用夹具获取配置和测试数据

示例：

```python
import pytest

@pytest.mark.api
@pytest.mark.auth
def test_login_success(test_config, base_url):
    """测试成功登录"""
    # 测试逻辑
    pass
```

### 添加新的配置

在 `config/test_config.py` 中的 `TestConfigManager` 类中添加新的配置项。

### 添加新的工具函数

在 `utils/test_helpers.py` 中添加新的工具函数或工具类。

## 注意事项

1. 测试前确保后端服务已启动
2. 测试数据会在测试结束后自动清理
3. 性能测试可能需要较长时间，可以使用 `-m "not performance"` 跳过
4. 网络测试需要网络连接，离线环境下会跳过
5. 测试日志会保存到 `api_integration_test.log` 文件

## 故障排查

### 测试失败

1. 检查后端服务是否正常运行
2. 检查环境变量配置是否正确
3. 查看测试日志获取详细错误信息
4. 使用 `-v` 参数获取更详细的输出

### 连接超时

1. 检查网络连接
2. 增加 `API_TIMEOUT` 环境变量的值
3. 检查防火墙设置

### 认证失败

1. 检查测试用户是否已创建
2. 检查用户名和密码是否正确
3. 检查JWT令牌配置

## 持续集成

测试套件可以集成到CI/CD流水线中：

```yaml
# GitHub Actions示例
- name: Run API Integration Tests
  run: |
    cd backend
    pytest api_integration_tests/ --junitxml=test-results.xml
```

## 联系方式

如有问题或建议，请联系开发团队。