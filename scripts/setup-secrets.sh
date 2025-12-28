#!/bin/bash

# GitHub Secrets 设置脚本
# 使用 GitHub CLI 设置 CI/CD 所需的密钥

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 GitHub CLI
if ! command -v gh &> /dev/null; then
    log_error "GitHub CLI 未安装，请先安装 gh"
    exit 1
fi

# 检查是否已登录
if ! gh auth status &> /dev/null; then
    log_error "请先使用 'gh auth login' 登录 GitHub"
    exit 1
fi

log_info "开始设置 GitHub Secrets..."

# 设置 Docker Hub 凭据
read -p "请输入 Docker Hub 用户名: " DOCKER_USERNAME
read -s -p "请输入 Docker Hub 密码: " DOCKER_PASSWORD
echo

gh secret set DOCKER_USERNAME --body "$DOCKER_USERNAME"
gh secret set DOCKER_PASSWORD --body "$DOCKER_PASSWORD"
log_info "✅ Docker Hub 凭据已设置"

# 设置服务器部署信息
read -p "请输入服务器 IP 地址: " HOST
read -p "请输入服务器用户名: " USERNAME
read -p "请输入 SSH 端口 (默认 22): " PORT
PORT=${PORT:-22}

gh secret set HOST --body "$HOST"
gh secret set USERNAME --body "$USERNAME"
gh secret set PORT --body "$PORT"

log_warn "请将 SSH 私钥内容复制到剪贴板，然后按回车键..."
read -p "按回车键继续..."
read -p "请粘贴 SSH 私钥内容: " SSH_KEY

gh secret set SSH_KEY --body "$SSH_KEY"
log_info "✅ 服务器部署信息已设置"

# 设置应用 URL
read -p "请输入后端 URL (如: https://api.your-domain.com): " BACKEND_URL
read -p "请输入前端 URL (如: https://your-domain.com): " FRONTEND_URL

gh secret set BACKEND_URL --body "$BACKEND_URL"
gh secret set FRONTEND_URL --body "$FRONTEND_URL"
log_info "✅ 应用 URL 已设置"

# 设置通知 Webhook (可选)
read -p "请输入 Slack Webhook URL (可选，直接回车跳过): " SLACK_WEBHOOK
if [ -n "$SLACK_WEBHOOK" ]; then
    gh secret set SLACK_WEBHOOK --body "$SLACK_WEBHOOK"
    log_info "✅ Slack 通知已设置"
fi

# 设置数据库密码
read -s -p "请输入数据库密码: " DB_PASSWORD
echo
gh secret set DB_PASSWORD --body "$DB_PASSWORD"

# 设置 Django Secret Key
DJANGO_SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
gh secret set SECRET_KEY --body "$DJANGO_SECRET_KEY"
log_info "✅ Django Secret Key 已生成并设置"

log_info "🎉 所有 GitHub Secrets 设置完成！"
log_info "现在可以推送代码触发 CI/CD 流程了"