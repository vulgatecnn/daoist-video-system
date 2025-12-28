#!/bin/bash

# 数据库恢复脚本
# 支持从本地备份或云存储恢复数据库

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
BACKUP_DIR="${BACKUP_DIR:-./backups}"
BACKUP_FILE=""
FORCE_RESTORE=false

# 从环境变量或 .env 文件加载配置
if [ -f ".env" ]; then
    source .env
fi

# 数据库配置
DB_NAME="${DB_NAME:-daoist_video_db}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-postgres}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

# 检查必要的工具
check_requirements() {
    log_info "检查恢复要求..."
    
    if ! command -v psql &> /dev/null; then
        log_error "psql 未安装"
        exit 1
    fi
    
    if ! command -v gunzip &> /dev/null; then
        log_error "gunzip 未安装"
        exit 1
    fi
    
    log_info "✅ 恢复要求检查通过"
}

# 列出可用的备份文件
list_backups() {
    log_info "可用的备份文件:"
    
    if [ -d "$BACKUP_DIR" ]; then
        local backups=($(ls -t "$BACKUP_DIR"/backup_*.sql.gz 2>/dev/null || true))
        
        if [ ${#backups[@]} -eq 0 ]; then
            log_warn "未找到本地备份文件"
        else
            for i in "${!backups[@]}"; do
                local file=$(basename "${backups[$i]}")
                local date=$(echo "$file" | sed 's/backup_\([0-9]\{8\}_[0-9]\{6\}\).*/\1/')
                local formatted_date=$(echo "$date" | sed 's/\([0-9]\{4\}\)\([0-9]\{2\}\)\([0-9]\{2\}\)_\([0-9]\{2\}\)\([0-9]\{2\}\)\([0-9]\{2\}\)/\1-\2-\3 \4:\5:\6/')
                local size=$(stat -c%s "${backups[$i]}" 2>/dev/null || stat -f%z "${backups[$i]}" 2>/dev/null)
                local size_mb=$((size / 1024 / 1024))
                
                echo "  $((i+1)). $file ($formatted_date, ${size_mb}MB)"
            done
        fi
    else
        log_warn "备份目录不存在: $BACKUP_DIR"
    fi
    
    # 列出 S3 备份 (如果配置了)
    if [ -n "$BACKUP_S3_BUCKET" ] && command -v aws &> /dev/null; then
        log_info "S3 备份文件:"
        aws s3 ls "s3://$BACKUP_S3_BUCKET/database-backups/" --human-readable | \
        grep "backup_" | tail -10 | \
        while read -r line; do
            echo "  S3: $line"
        done
    fi
}

# 从 S3 下载备份文件
download_from_s3() {
    local s3_file="$1"
    local local_file="$BACKUP_DIR/$s3_file"
    
    log_info "从 S3 下载备份文件: $s3_file"
    
    if [ ! -d "$BACKUP_DIR" ]; then
        mkdir -p "$BACKUP_DIR"
    fi
    
    if aws s3 cp "s3://$BACKUP_S3_BUCKET/database-backups/$s3_file" "$local_file"; then
        log_info "✅ 备份文件下载完成"
        BACKUP_FILE="$local_file"
    else
        log_error "S3 下载失败"
        exit 1
    fi
}

# 验证备份文件
verify_backup_file() {
    if [ ! -f "$BACKUP_FILE" ]; then
        log_error "备份文件不存在: $BACKUP_FILE"
        exit 1
    fi
    
    # 检查文件是否为有效的 gzip 文件
    if ! gunzip -t "$BACKUP_FILE" 2>/dev/null; then
        log_error "备份文件损坏或不是有效的 gzip 文件"
        exit 1
    fi
    
    log_info "✅ 备份文件验证通过"
}

# 创建数据库备份 (恢复前)
create_pre_restore_backup() {
    if [ "$FORCE_RESTORE" = false ]; then
        log_info "创建恢复前备份..."
        
        local pre_restore_backup="$BACKUP_DIR/pre_restore_$(date +%Y%m%d_%H%M%S).sql"
        
        export PGPASSWORD="$DB_PASSWORD"
        
        if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
            --no-owner --no-privileges --clean --if-exists \
            | gzip > "${pre_restore_backup}.gz"; then
            
            log_info "✅ 恢复前备份完成: $(basename "${pre_restore_backup}.gz")"
        else
            log_warn "恢复前备份失败，继续恢复流程"
        fi
        
        unset PGPASSWORD
    fi
}

# 停止相关服务 (如果在 Docker 环境中)
stop_services() {
    if command -v docker-compose &> /dev/null && [ -f "docker-compose.yml" ]; then
        log_info "停止相关服务..."
        
        # 停止后端服务但保持数据库运行
        docker-compose stop backend celery celery-beat 2>/dev/null || true
        
        log_info "✅ 服务已停止"
    fi
}

# 启动相关服务
start_services() {
    if command -v docker-compose &> /dev/null && [ -f "docker-compose.yml" ]; then
        log_info "启动相关服务..."
        
        docker-compose up -d backend celery celery-beat 2>/dev/null || true
        
        # 等待服务启动
        sleep 10
        
        log_info "✅ 服务已启动"
    fi
}

# 执行数据库恢复
perform_restore() {
    log_info "开始恢复数据库: $DB_NAME"
    
    export PGPASSWORD="$DB_PASSWORD"
    
    # 解压并恢复数据库
    if gunzip -c "$BACKUP_FILE" | psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1; then
        log_info "✅ 数据库恢复完成"
    else
        log_error "数据库恢复失败"
        unset PGPASSWORD
        exit 1
    fi
    
    unset PGPASSWORD
}

# 验证恢复结果
verify_restore() {
    log_info "验证恢复结果..."
    
    export PGPASSWORD="$DB_PASSWORD"
    
    # 检查数据库连接
    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
        log_info "✅ 数据库连接正常"
    else
        log_error "数据库连接失败"
        unset PGPASSWORD
        exit 1
    fi
    
    # 检查表数量
    local table_count=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | xargs)
    
    if [ "$table_count" -gt 0 ]; then
        log_info "✅ 数据库包含 $table_count 个表"
    else
        log_warn "数据库中没有找到表，恢复可能不完整"
    fi
    
    unset PGPASSWORD
}

# 运行数据库迁移
run_migrations() {
    log_info "运行数据库迁移..."
    
    if command -v docker-compose &> /dev/null && [ -f "docker-compose.yml" ]; then
        # Docker 环境
        if docker-compose exec -T backend python manage.py migrate; then
            log_info "✅ 数据库迁移完成"
        else
            log_warn "数据库迁移失败"
        fi
    else
        # 本地环境
        if [ -f "backend/manage.py" ]; then
            cd backend
            if python manage.py migrate; then
                log_info "✅ 数据库迁移完成"
            else
                log_warn "数据库迁移失败"
            fi
            cd ..
        fi
    fi
}

# 发送通知
send_notification() {
    local status=$1
    local message="数据库恢复${status}: 时间=$(date), 文件=$(basename "$BACKUP_FILE")"
    
    # Slack 通知
    if [ -n "$SLACK_WEBHOOK" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"$message\"}" \
            "$SLACK_WEBHOOK" 2>/dev/null || true
    fi
    
    log_info "通知已发送: $message"
}

# 主恢复流程
main() {
    log_info "开始数据库恢复流程..."
    
    check_requirements
    
    if [ -z "$BACKUP_FILE" ]; then
        log_error "请指定备份文件"
        list_backups
        exit 1
    fi
    
    verify_backup_file
    
    # 确认恢复操作
    if [ "$FORCE_RESTORE" = false ]; then
        echo -e "${YELLOW}警告: 此操作将覆盖当前数据库内容${NC}"
        echo -e "备份文件: $BACKUP_FILE"
        echo -e "目标数据库: $DB_NAME@$DB_HOST:$DB_PORT"
        echo ""
        read -p "确认继续恢复? (yes/no): " confirm
        
        if [ "$confirm" != "yes" ]; then
            log_info "恢复操作已取消"
            exit 0
        fi
    fi
    
    create_pre_restore_backup
    stop_services
    perform_restore
    verify_restore
    run_migrations
    start_services
    
    send_notification "成功"
    log_info "🎉 数据库恢复流程完成！"
}

# 显示帮助信息
show_help() {
    echo "数据库恢复脚本"
    echo ""
    echo "用法: $0 [选项] <备份文件>"
    echo ""
    echo "选项:"
    echo "  -h, --help          显示帮助信息"
    echo "  -l, --list          列出可用的备份文件"
    echo "  -f, --force         强制恢复，不创建恢复前备份"
    echo "  -s, --s3 <文件名>   从 S3 下载并恢复指定文件"
    echo ""
    echo "示例:"
    echo "  $0 backups/backup_20231228_120000.sql.gz"
    echo "  $0 --s3 backup_20231228_120000.sql.gz"
    echo "  $0 --list"
}

# 处理命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -l|--list)
            list_backups
            exit 0
            ;;
        -f|--force)
            FORCE_RESTORE=true
            shift
            ;;
        -s|--s3)
            if [ -n "$2" ]; then
                download_from_s3 "$2"
                shift 2
            else
                log_error "--s3 选项需要指定文件名"
                exit 1
            fi
            ;;
        -*)
            log_error "未知选项: $1"
            show_help
            exit 1
            ;;
        *)
            if [ -z "$BACKUP_FILE" ]; then
                BACKUP_FILE="$1"
            else
                log_error "只能指定一个备份文件"
                exit 1
            fi
            shift
            ;;
    esac
done

# 错误处理
trap 'log_error "恢复过程中发生错误"; send_notification "失败"; start_services; exit 1' ERR

# 执行主函数
main