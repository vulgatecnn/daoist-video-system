# 道教视频系统 CI/CD 完整指南

## 🎯 概述

本指南提供了道教视频系统完整的 CI/CD 解决方案，包括自动化测试、构建、部署、监控和回滚机制。

## 📋 功能特性

### ✅ 已实现的功能

- **持续集成 (CI)**
  - 自动化代码测试 (后端 + 前端)
  - 代码质量检查 (Linting, 格式化)
  - 安全扫描 (Bandit)
  - Docker 镜像构建和推送
  - 集成测试和性能测试

- **持续部署 (CD)**
  - 自动化部署到生产环境
  - 健康检查和验证
  - 回滚机制
  - 通知系统 (Slack, 邮件)

- **监控和告警**
  - Prometheus + Grafana 监控
  - Alertmanager 告警管理
  - 日志聚合 (Loki + Promtail)
  - 分布式追踪 (Jaeger)

- **数据管理**
  - 自动化数据库备份
  - 备份恢复机制
  - 云存储集成 (S3)

- **性能测试**
  - Locust 负载测试
  - 自动化性能基准检查
  - 性能报告生成

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆仓库
git clone https://github.com/your-username/daoist-video-system.git
cd daoist-video-system

# 复制环境变量模板
cp .env.example .env

# 编辑环境变量
nano .env
```

### 2. 设置权限

```bash
# 设置脚本权限
chmod +x scripts/setup-permissions.sh
./scripts/setup-permissions.sh
```

### 3. 配置 GitHub Secrets

```bash
# 使用自动化脚本
chmod +x scripts/setup-secrets.sh
./scripts/setup-secrets.sh
```

### 4. 启动开发环境

```bash
# 启动基础服务
docker-compose up -d

# 启动监控服务
docker-compose -f docker-compose.monitoring.yml up -d
```

## 📁 项目结构

```
├── .github/workflows/          # GitHub Actions 工作流
│   ├── ci.yml                 # 持续集成流程
│   └── deploy.yml             # 部署流程
├── scripts/                   # 自动化脚本
│   ├── deploy.sh             # 部署脚本
│   ├── backup-database.sh    # 数据库备份
│   ├── restore-database.sh   # 数据库恢复
│   ├── rollback.sh           # 回滚脚本
│   ├── setup-secrets.sh      # GitHub Secrets 设置
│   └── setup-permissions.sh  # 权限设置
├── monitoring/               # 监控配置
│   ├── prometheus.yml        # Prometheus 配置
│   ├── alertmanager.yml      # 告警管理配置
│   └── alert_rules.yml       # 告警规则
├── performance/              # 性能测试
│   ├── locustfile.py         # Locust 测试脚本
│   └── run-performance-tests.sh # 性能测试运行脚本
├── nginx/                    # Nginx 配置
│   ├── nginx.conf            # 主配置文件
│   └── sites-available/      # 站点配置
├── docker-compose.yml        # 开发环境
├── docker-compose.prod.yml   # 生产环境
├── docker-compose.monitoring.yml # 监控服务
└── .env.example              # 环境变量模板
```

## 🔄 CI/CD 工作流程

### 持续集成流程

1. **代码推送** → 触发 GitHub Actions
2. **环境设置** → Python 3.9 + Node.js 18
3. **依赖安装** → 后端和前端依赖
4. **代码质量检查** → Flake8, Black, ESLint
5. **单元测试** → Django 测试 + Jest 测试
6. **集成测试** → API 端点测试
7. **安全扫描** → Bandit 安全检查
8. **Docker 构建** → 构建并推送镜像

### 持续部署流程

1. **镜像拉取** → 从 Docker Registry 拉取最新镜像
2. **服务停止** → 优雅停止当前服务
3. **数据库备份** → 自动备份当前数据
4. **服务部署** → 启动新版本服务
5. **数据库迁移** → 运行 Django 迁移
6. **健康检查** → 验证服务正常运行
7. **通知发送** → 发送部署结果通知

## 🛠️ 使用指南

### 部署到生产环境

```bash
# 手动部署
./scripts/deploy.sh production

# 查看部署日志
docker-compose -f docker-compose.prod.yml logs -f
```

### 数据库管理

```bash
# 备份数据库
./scripts/backup-database.sh

# 恢复数据库
./scripts/restore-database.sh backups/backup_20231228_120000.sql.gz

# 从 S3 恢复
./scripts/restore-database.sh --s3 backup_20231228_120000.sql.gz
```

### 性能测试

```bash
# 运行冒烟测试
./performance/run-performance-tests.sh --type smoke

# 运行负载测试
./performance/run-performance-tests.sh --type load --users 100 --duration 600s

# 运行压力测试
./performance/run-performance-tests.sh --type stress
```

### 应用回滚

```bash
# 回滚到上一个 Git 提交
./scripts/rollback.sh abc1234

# 回滚到指定 Docker 镜像版本
./scripts/rollback.sh v1.2.3

# 查看可用的回滚目标
./scripts/rollback.sh --list
```

## 📊 监控和告警

### 访问监控面板

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Alertmanager**: http://localhost:9093

### 关键监控指标

- **应用指标**: 请求数量、响应时间、错误率
- **系统指标**: CPU、内存、磁盘使用率
- **数据库指标**: 连接数、查询性能
- **容器指标**: 容器资源使用情况

### 告警配置

告警会通过以下方式发送：
- Slack 通知 (#alerts 频道)
- 邮件通知 (admin@your-domain.com)
- 企业微信 (可选)

## 🔧 配置说明

### 环境变量配置

关键环境变量说明：

```bash
# 基础配置
ENVIRONMENT=production
SECRET_KEY=your-secret-key
DEBUG=False

# 数据库配置
DB_NAME=daoist_video_db
DB_USER=postgres
DB_PASSWORD=your-db-password

# Redis 配置
REDIS_PASSWORD=your-redis-password

# 监控配置
GRAFANA_PASSWORD=your-grafana-password
SLACK_WEBHOOK=your-slack-webhook-url

# 云存储配置 (可选)
BACKUP_S3_BUCKET=your-backup-bucket
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
```

### GitHub Secrets 配置

必需的 GitHub Secrets：

```
DOCKER_USERNAME          # Docker Hub 用户名
DOCKER_PASSWORD          # Docker Hub 密码
HOST                     # 服务器 IP 地址
USERNAME                 # 服务器用户名
SSH_KEY                  # SSH 私钥
SECRET_KEY               # Django 密钥
DB_PASSWORD              # 数据库密码
BACKEND_URL              # 后端 API 地址
FRONTEND_URL             # 前端应用地址
SLACK_WEBHOOK            # Slack 通知 URL (可选)
```

## 🚨 故障排查

### 常见问题

#### 1. 部署失败

```bash
# 查看容器日志
docker-compose -f docker-compose.prod.yml logs backend

# 检查容器状态
docker-compose -f docker-compose.prod.yml ps

# 手动重启服务
docker-compose -f docker-compose.prod.yml restart backend
```

#### 2. 数据库连接问题

```bash
# 检查数据库容器
docker-compose -f docker-compose.prod.yml exec db psql -U postgres

# 查看数据库日志
docker-compose -f docker-compose.prod.yml logs db
```

#### 3. 监控服务异常

```bash
# 重启监控服务
docker-compose -f docker-compose.monitoring.yml restart prometheus grafana

# 检查配置文件
docker-compose -f docker-compose.monitoring.yml config
```

### 日志查看

```bash
# 应用日志
tail -f backend/logs/django.log

# Nginx 日志
docker-compose -f docker-compose.prod.yml logs nginx

# 系统日志
journalctl -u docker -f
```

## 🔒 安全最佳实践

1. **密钥管理**
   - 使用 GitHub Secrets 管理敏感信息
   - 定期轮换密钥和密码
   - 使用强密码策略

2. **网络安全**
   - 配置防火墙规则
   - 使用 HTTPS 和 SSL 证书
   - 限制不必要的端口访问

3. **容器安全**
   - 定期更新基础镜像
   - 扫描镜像漏洞
   - 使用非 root 用户运行容器

4. **访问控制**
   - 限制 SSH 访问
   - 使用密钥认证
   - 定期审查用户权限

## 📈 性能优化

### 应用层优化

- 数据库查询优化
- Redis 缓存策略
- 静态文件 CDN
- 代码分割和懒加载

### 基础设施优化

- 负载均衡配置
- 数据库读写分离
- 容器资源限制
- 网络优化

## 🔄 维护任务

### 定期维护

```bash
# 每日任务
./scripts/backup-database.sh

# 每周任务
docker system prune -f
./scripts/setup-permissions.sh --verify

# 每月任务
# 更新依赖包
# 安全补丁更新
# 性能基准测试
```

### 监控检查

- 检查磁盘空间使用
- 监控内存和 CPU 使用率
- 验证备份完整性
- 检查日志文件大小

## 📚 参考资源

- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [Docker Compose 文档](https://docs.docker.com/compose/)
- [Prometheus 文档](https://prometheus.io/docs/)
- [Grafana 文档](https://grafana.com/docs/)
- [Django 部署指南](https://docs.djangoproject.com/en/stable/howto/deployment/)

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

---

**注意**: 在生产环境中使用前，请确保：
1. 所有密钥和密码已正确配置
2. 防火墙和安全组规则已设置
3. SSL 证书已安装和配置
4. 监控和告警已测试
5. 备份和恢复流程已验证