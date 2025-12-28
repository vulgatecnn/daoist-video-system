# CI/CD 部署指南

## 概述

本文档介绍如何为道教视频系统设置完整的 CI/CD 流程，包括自动化测试、构建、部署和监控。

## 架构概览

```
GitHub Repository
       ↓
   GitHub Actions
       ↓
   Docker Registry
       ↓
   Production Server
       ↓
   Monitoring & Alerts
```

## 前置要求

### 开发环境
- Git
- Docker & Docker Compose
- Node.js 18+
- Python 3.9+
- GitHub CLI (可选)

### 生产环境
- Linux 服务器 (Ubuntu 20.04+ 推荐)
- Docker & Docker Compose
- Nginx (可选，如果不使用容器化 Nginx)
- SSL 证书

## 设置步骤

### 1. 配置 GitHub Secrets

运行自动化脚本：
```bash
chmod +x scripts/setup-secrets.sh
./scripts/setup-secrets.sh
```

或手动在 GitHub 仓库设置中添加以下 Secrets：

#### Docker Hub 配置
- `DOCKER_USERNAME`: Docker Hub 用户名
- `DOCKER_PASSWORD`: Docker Hub 密码

#### 服务器配置
- `HOST`: 服务器 IP 地址
- `USERNAME`: 服务器用户名
- `SSH_KEY`: SSH 私钥
- `PORT`: SSH 端口 (默认 22)

#### 应用配置
- `SECRET_KEY`: Django 密钥
- `DB_PASSWORD`: 数据库密码
- `BACKEND_URL`: 后端 API 地址
- `FRONTEND_URL`: 前端应用地址

#### 通知配置 (可选)
- `SLACK_WEBHOOK`: Slack 通知 Webhook

### 2. 服务器准备

#### 安装 Docker
```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 将用户添加到 docker 组
sudo usermod -aG docker $USER
```

#### 创建应用目录
```bash
sudo mkdir -p /opt/daoist-video-system
sudo chown $USER:$USER /opt/daoist-video-system
cd /opt/daoist-video-system

# 克隆仓库
git clone https://github.com/vulgatecnn/daoist-video-system.git .
```

#### 配置环境变量
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量
nano .env
```

### 3. SSL 证书配置 (生产环境)

#### 使用 Let's Encrypt
```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com -d api.your-domain.com

# 设置自动续期
sudo crontab -e
# 添加以下行：
# 0 12 * * * /usr/bin/certbot renew --quiet
```

### 4. 部署应用

#### 首次部署
```bash
# 使用部署脚本
chmod +x scripts/deploy.sh
./scripts/deploy.sh production
```

#### 手动部署
```bash
# 拉取最新镜像
docker-compose -f docker-compose.prod.yml pull

# 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 运行数据库迁移
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate

# 收集静态文件
docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput
```

## CI/CD 工作流程

### 1. 持续集成 (CI)

当代码推送到 `master` 分支或创建 Pull Request 时：

1. **代码检出**: 获取最新代码
2. **环境设置**: 配置 Python 和 Node.js 环境
3. **依赖安装**: 安装后端和前端依赖
4. **代码质量检查**: 运行 linting 和格式检查
5. **单元测试**: 运行后端和前端测试
6. **集成测试**: 运行 API 集成测试
7. **安全扫描**: 检查安全漏洞
8. **构建验证**: 验证 Docker 镜像构建

### 2. 持续部署 (CD)

当代码合并到 `master` 分支时：

1. **构建镜像**: 构建 Docker 镜像
2. **推送镜像**: 推送到 Docker Registry
3. **部署到服务器**: 通过 SSH 部署到生产环境
4. **健康检查**: 验证服务正常运行
5. **通知**: 发送部署结果通知

## 监控和告警

### Prometheus 监控指标

- **应用指标**: 请求数量、响应时间、错误率
- **系统指标**: CPU、内存、磁盘使用率
- **数据库指标**: 连接数、查询性能
- **容器指标**: 容器资源使用情况

### Grafana 仪表板

访问 `http://your-server:3000` 查看监控仪表板：

- 系统概览
- 应用性能
- 数据库状态
- 错误日志

### 告警规则

- 服务不可用
- 高错误率 (>10%)
- 响应时间过长 (>2秒)
- 资源使用率过高
- 数据库异常

## 故障排查

### 常见问题

#### 1. 部署失败
```bash
# 查看容器日志
docker-compose -f docker-compose.prod.yml logs backend
docker-compose -f docker-compose.prod.yml logs frontend

# 检查容器状态
docker-compose -f docker-compose.prod.yml ps
```

#### 2. 数据库连接问题
```bash
# 检查数据库容器
docker-compose -f docker-compose.prod.yml exec db psql -U postgres -d daoist_video_db

# 查看数据库日志
docker-compose -f docker-compose.prod.yml logs db
```

#### 3. 静态文件问题
```bash
# 重新收集静态文件
docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput

# 检查 Nginx 配置
docker-compose -f docker-compose.prod.yml exec nginx nginx -t
```

### 日志查看

```bash
# 应用日志
tail -f logs/django.log

# Nginx 日志
docker-compose -f docker-compose.prod.yml logs nginx

# 系统日志
journalctl -u docker -f
```

## 性能优化

### 1. 数据库优化
- 配置连接池
- 添加适当索引
- 定期清理日志

### 2. 缓存优化
- Redis 缓存配置
- 静态文件缓存
- 数据库查询缓存

### 3. 容器优化
- 资源限制配置
- 镜像大小优化
- 多阶段构建

## 安全最佳实践

1. **密钥管理**: 使用 GitHub Secrets 管理敏感信息
2. **网络安全**: 配置防火墙和 VPN
3. **容器安全**: 定期更新基础镜像
4. **访问控制**: 限制 SSH 访问和 sudo 权限
5. **备份策略**: 定期备份数据库和重要文件

## 扩展和维护

### 水平扩展
- 负载均衡配置
- 多实例部署
- 数据库读写分离

### 维护任务
- 定期更新依赖
- 清理旧镜像和容器
- 监控磁盘空间
- 备份验证

## 参考资源

- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [Docker Compose 文档](https://docs.docker.com/compose/)
- [Prometheus 文档](https://prometheus.io/docs/)
- [Grafana 文档](https://grafana.com/docs/)