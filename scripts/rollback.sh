#!/bin/bash

# 应用回滚脚本
# 支持快速回滚到上一个稳定版本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

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

# 配置变量
ENVIRONMENT="${ENVIRONMENT:-production}"
BACKUP_DIR="./backups"
ROLLBACK_TARGET=""
FORCE_ROLLBACK=false
DRY_RUN=false

# 从环境变量加载配置
if [ -f ".env" ]; then
    source .env
fi

# Docker 配置
DOCKER_USERNAME="${DOCKER_USERNAME:-your-docker-username}"

# 检查必要工具
check_requirements() {
    log_info "检查回滚要求..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装"
        exit 1
    fi
    
    if ! command -v git &> /dev/null; then
        log_error "Git 未安装"
        exit 1
    fi
    
    log_info "✅ 回滚要求检查通过"
}

# 获取当前部署信息
get_current_deployment() {
    log_info "获取当前部署信息..."
    
    # 获取当前 Git 提交
    CURRENT_COMMIT=$(git rev-parse HEAD)
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    
    # 获取当前 Docker 镜像标签
    if [ "$ENVIRONMENT" = "production" ]; then
        CURRENT_BACKEND_IMAGE=$(docker-compose -f docker-compose.prod.yml images backend | tail -n 1 | awk '{print $2":"$3}')
        CURRENT_FRONTEND_IMAGE=$(docker-compose -f docker-compose.prod.yml images frontend | tail -n 1 | awk '{print $2":"$3}')
    else
        CURRENT_BACKEND_IMAGE=$(docker-compose images backend | tail -n 1 | awk '{print $2":"$3}')
        CURRENT_FRONTEND_IMAGE=$(docker-compose images frontend | tail -n 1 | awk '{print $2":"$3}')
    fi
    
    log_info "当前部署信息:"
    log_info "  Git 提交: $CURRENT_COMMIT"
    log_info "  Git 分支: $CURRENT_BRANCH"
    log_info "  后端镜像: $CURRENT_BACKEND_IMAGE"
    log_info "  前端镜像: $CURRENT_FRONTEND_IMAGE"
}

# 列出可用的回滚目标
list_rollback_targets() {
    log_info "可用的回滚目标:"
    
    echo "📋 Git 提交历史 (最近 10 个):"
    git log --oneline -10 | nl -v0
    
    echo ""
    echo "🐳 Docker 镜像标签:"
    
    # 列出本地可用的镜像
    if docker images "${DOCKER_USERNAME}/daoist-video-backend" --format "table {{.Tag}}\t{{.CreatedAt}}" | head -10; then
        echo ""
    else
        log_warn "未找到本地后端镜像"
    fi
    
    # 列出备份文件
    if [ -d "$BACKUP_DIR" ]; then
        echo "💾 数据库备份文件:"
        ls -lt "$BACKUP_DIR"/backup_*.sql.gz 2>/dev/null | head -5 || log_warn "未找到数据库备份"
    fi
}

# 验证回滚目标
validate_rollback_target() {
    local target="$1"
    
    log_info "验证回滚目标: $target"
    
    # 检查是否为 Git 提交哈希
    if git cat-file -e "$target" 2>/dev/null; then
        log_info "✅ 有效的 Git 提交: $target"
        return 0
    fi
    
    # 检查是否为 Docker 镜像标签
    if docker images "${DOCKER_USERNAME}/daoist-video-backend:$target" --format "{{.ID}}" | grep -q .; then
        log_info "✅ 有效的 Docker 镜像标签: $target"
        return 0
    fi
    
    log_error "无效的回滚目标: $target"
    return 1
}

# 创建回滚前备份
create_rollback_backup() {
    log_info "创建回滚前备份..."
    
    local backup_timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="$BACKUP_DIR/rollback_backup_${backup_timestamp}.sql.gz"
    
    # 创建备份目录
    mkdir -p "$BACKUP_DIR"
    
    # 备份数据库
    if [ "$ENVIRONMENT" = "production" ]; then
        docker-compose -f docker-compose.prod.yml exec -T db pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$backup_file"
    else
        docker-compose exec -T db pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$backup_file"
    fi
    
    if [ -f "$backup_file" ]; then
        log_info "✅ 回滚前备份完成: $(basename "$backup_file")"
    else
        log_error "回滚前备份失败"
        exit 1
    fi
}

# 停止当前服务
stop_current_services() {
    log_info "停止当前服务..."
    
    if [ "$ENVIRONMENT" = "production" ]; then
        docker-compose -f docker-compose.prod.yml down
    else
        docker-compose down
    fi
    
    log_info "✅ 服务已停止"
}

# 回滚到指定 Git 提交
rollback_to_git_commit() {
    local commit="$1"
    
    log_info "回滚到 Git 提交: $commit"
    
    # 检出指定提交
    git checkout "$commit"
    
    # 重新构建镜像
    if [ "$ENVIRONMENT" = "production" ]; then
        docker-compose -f docker-compose.prod.yml build --no-cache
    else
        docker-compose build --no-cache
    fi
    
    log_info "✅ Git 回滚完成"
}

# 回滚到指定 Docker 镜像
rollback_to_docker_image() {
    local tag="$1"
    
    log_info "回滚到 Docker 镜像标签: $tag"
    
    # 更新 docker-compose 文件中的镜像标签
    if [ "$ENVIRONMENT" = "production" ]; then
        # 临时修改生产环境配置
        sed -i.bak "s|${DOCKER_USERNAME}/daoist-video-backend:latest|${DOCKER_USERNAME}/daoist-video-backend:$tag|g" docker-compose.prod.yml
        sed -i.bak "s|${DOCKER_USERNAME}/daoist-video-frontend:latest|${DOCKER_USERNAME}/daoist-video-frontend:$tag|g" docker-compose.prod.yml
    fi
    
    log_info "✅ Docker 镜像回滚配置完成"
}

# 启动回滚后的服务
start_rollback_services() {
    log_info "启动回滚后的服务..."
    
    if [ "$ENVIRONMENT" = "production" ]; then
        docker-compose -f docker-compose.prod.yml up -d
    else
        docker-compose up -d
    fi
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 30
    
    log_info "✅ 服务已启动"
}

# 验证回滚结果
verify_rollback() {
    log_info "验证回滚结果..."
    
    local max_attempts=10
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        log_info "验证尝试 $attempt/$max_attempts"
        
        # 检查健康状态
        if curl -f http://localhost:8000/health/ > /dev/null 2>&1; then
            log_info "✅ 后端服务健康检查通过"
            
            # 检查前端
            if curl -f http://localhost/ > /dev/null 2>&1; then
                log_info "✅ 前端服务健康检查通过"
                log_info "✅ 回滚验证成功"
                return 0
            fi
        fi
        
        log_warn "健康检查失败，等待 10 秒后重试..."
        sleep 10
        ((attempt++))
    done
    
    log_error "回滚验证失败"
    return 1
}

# 恢复 docker-compose 配置
restore_compose_config() {
    if [ "$ENVIRONMENT" = "production" ] && [ -f "docker-compose.prod.yml.bak" ]; then
        log_info "恢复 docker-compose 配置..."
        mv docker-compose.prod.yml.bak docker-compose.prod.yml
    fi
}

# 发送回滚通知
send_rollback_notification() {
    local status=$1
    local target=$2
    local message="应用回滚${status}: 目标=${target}, 环境=${ENVIRONMENT}, 时间=$(date)"
    
    # Slack 通知
    if [ -n "$SLACK_WEBHOOK" ]; then
        local color="good"
        if [ "$status" = "失败" ]; then
            color="danger"
        fi
        
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"$message\", \"color\":\"$color\"}" \
            "$SLACK_WEBHOOK" 2>/dev/null || true
    fi
    
    # 邮件通知
    if [ -n "$ALERT_EMAIL" ] && command -v mail &> /dev/null; then
        echo "$message" | mail -s "应用回滚通知" "$ALERT_EMAIL" 2>/dev/null || true
    fi
    
    log_info "通知已发送: $message"
}

# 主回滚流程
main() {
    log_info "开始应用回滚流程..."
    
    check_requirements
    get_current_deployment
    
    if [ -z "$ROLLBACK_TARGET" ]; then
        log_error "请指定回滚目标"
        list_rollback_targets
        exit 1
    fi
    
    if ! validate_rollback_target "$ROLLBACK_TARGET"; then
        exit 1
    fi
    
    # 确认回滚操作
    if [ "$FORCE_ROLLBACK" = false ]; then
        echo -e "${YELLOW}警告: 此操作将回滚应用到指定版本${NC}"
        echo -e "当前版本: $CURRENT_COMMIT"
        echo -e "回滚目标: $ROLLBACK_TARGET"
        echo -e "环境: $ENVIRONMENT"
        echo ""
        read -p "确认继续回滚? (yes/no): " confirm
        
        if [ "$confirm" != "yes" ]; then
            log_info "回滚操作已取消"
            exit 0
        fi
    fi
    
    if [ "$DRY_RUN" = true ]; then
        log_info "模拟运行模式 - 不执行实际回滚"
        log_info "将会执行以下操作:"
        log_info "1. 创建回滚前备份"
        log_info "2. 停止当前服务"
        log_info "3. 回滚到: $ROLLBACK_TARGET"
        log_info "4. 启动回滚后服务"
        log_info "5. 验证回滚结果"
        exit 0
    fi
    
    # 执行回滚
    create_rollback_backup
    stop_current_services
    
    # 根据目标类型执行不同的回滚策略
    if git cat-file -e "$ROLLBACK_TARGET" 2>/dev/null; then
        rollback_to_git_commit "$ROLLBACK_TARGET"
    else
        rollback_to_docker_image "$ROLLBACK_TARGET"
    fi
    
    start_rollback_services
    
    if verify_rollback; then
        send_rollback_notification "成功" "$ROLLBACK_TARGET"
        log_info "🎉 应用回滚成功完成！"
    else
        restore_compose_config
        send_rollback_notification "失败" "$ROLLBACK_TARGET"
        log_error "💥 应用回滚失败"
        exit 1
    fi
}

# 显示帮助信息
show_help() {
    echo "应用回滚脚本"
    echo ""
    echo "用法: $0 [选项] <回滚目标>"
    echo ""
    echo "选项:"
    echo "  -h, --help          显示帮助信息"
    echo "  -l, --list          列出可用的回滚目标"
    echo "  -f, --force         强制回滚，不需要确认"
    echo "  -e, --env ENV       指定环境 (development|production)"
    echo "  --dry-run           模拟运行，不执行实际回滚"
    echo ""
    echo "回滚目标:"
    echo "  Git 提交哈希        如: abc1234"
    echo "  Docker 镜像标签     如: v1.2.3"
    echo ""
    echo "示例:"
    echo "  $0 abc1234                    # 回滚到指定 Git 提交"
    echo "  $0 v1.2.3                    # 回滚到指定镜像版本"
    echo "  $0 --list                    # 列出可用回滚目标"
    echo "  $0 --dry-run abc1234         # 模拟回滚"
}

# 处理命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -l|--list)
            list_rollback_targets
            exit 0
            ;;
        -f|--force)
            FORCE_ROLLBACK=true
            shift
            ;;
        -e|--env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -*)
            log_error "未知选项: $1"
            show_help
            exit 1
            ;;
        *)
            if [ -z "$ROLLBACK_TARGET" ]; then
                ROLLBACK_TARGET="$1"
            else
                log_error "只能指定一个回滚目标"
                exit 1
            fi
            shift
            ;;
    esac
done

# 错误处理
trap 'log_error "回滚过程中发生错误"; restore_compose_config; send_rollback_notification "失败" "$ROLLBACK_TARGET"; exit 1' ERR

# 执行主函数
main