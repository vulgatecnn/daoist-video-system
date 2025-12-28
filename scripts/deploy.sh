#!/bin/bash

# 道教视频系统部署脚本
# 使用方法: ./scripts/deploy.sh [环境]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查参数
ENVIRONMENT=${1:-production}
log_info "部署环境: $ENVIRONMENT"

# 检查必要的工具
check_requirements() {
    log_info "检查部署要求..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装"
        exit 1
    fi
    
    log_info "✅ 部署要求检查通过"
}

# 备份数据库
backup_database() {
    log_info "备份数据库..."
    
    if [ "$ENVIRONMENT" = "production" ]; then
        docker-compose -f docker-compose.prod.yml exec -T db pg_dump -U $DB_USER $DB_NAME > "backups/backup_$(date +%Y%m%d_%H%M%S).sql"
        log_info "✅ 数据库备份完成"
    else
        log_warn "开发环境跳过数据库备份"
    fi
}

# 拉取最新代码
pull_code() {
    log_info "拉取最新代码..."
    git pull origin master
    log_info "✅ 代码更新完成"
}

# 构建镜像
build_images() {
    log_info "构建 Docker 镜像..."
    
    if [ "$ENVIRONMENT" = "production" ]; then
        docker-compose -f docker-compose.prod.yml build --no-cache
    else
        docker-compose build --no-cache
    fi
    
    log_info "✅ 镜像构建完成"
}

# 部署服务
deploy_services() {
    log_info "部署服务..."
    
    if [ "$ENVIRONMENT" = "production" ]; then
        # 生产环境部署
        docker-compose -f docker-compose.prod.yml down
        docker-compose -f docker-compose.prod.yml up -d
    else
        # 开发环境部署
        docker-compose down
        docker-compose up -d
    fi
    
    log_info "✅ 服务部署完成"
}

# 运行数据库迁移
run_migrations() {
    log_info "运行数据库迁移..."
    
    # 等待数据库启动
    sleep 10
    
    if [ "$ENVIRONMENT" = "production" ]; then
        docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate
        docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput
    else
        docker-compose exec backend python manage.py migrate
        docker-compose exec backend python manage.py collectstatic --noinput
    fi
    
    log_info "✅ 数据库迁移完成"
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    
    # 等待服务启动
    sleep 30
    
    # 检查后端
    if curl -f http://localhost:8000/health/ > /dev/null 2>&1; then
        log_info "✅ 后端服务健康"
    else
        log_error "❌ 后端服务异常"
        return 1
    fi
    
    # 检查前端
    if curl -f http://localhost/ > /dev/null 2>&1; then
        log_info "✅ 前端服务健康"
    else
        log_error "❌ 前端服务异常"
        return 1
    fi
    
    log_info "✅ 所有服务健康检查通过"
}

# 清理旧镜像
cleanup() {
    log_info "清理旧镜像..."
    docker image prune -f
    log_info "✅ 清理完成"
}

# 发送通知
send_notification() {
    local status=$1
    local message="部署${status}: 环境=${ENVIRONMENT}, 时间=$(date), 提交=$(git rev-parse --short HEAD)"
    
    if [ -n "$SLACK_WEBHOOK" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"$message\"}" \
            "$SLACK_WEBHOOK"
    fi
    
    log_info "通知已发送: $message"
}

# 主部署流程
main() {
    log_info "开始部署道教视频系统..."
    
    # 加载环境变量
    if [ -f ".env" ]; then
        source .env
    else
        log_warn "未找到 .env 文件，使用默认配置"
    fi
    
    # 执行部署步骤
    check_requirements
    
    if [ "$ENVIRONMENT" = "production" ]; then
        backup_database
    fi
    
    pull_code
    build_images
    deploy_services
    run_migrations
    
    if health_check; then
        cleanup
        send_notification "成功"
        log_info "🎉 部署成功完成！"
    else
        send_notification "失败"
        log_error "💥 部署失败，请检查日志"
        exit 1
    fi
}

# 错误处理
trap 'log_error "部署过程中发生错误"; send_notification "失败"; exit 1' ERR

# 执行主函数
main "$@"