#!/bin/bash

# 数据库备份脚本
# 支持本地备份和云存储备份

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
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="backup_${TIMESTAMP}.sql"
COMPRESSED_FILE="${BACKUP_FILE}.gz"

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
    log_info "检查备份要求..."
    
    if ! command -v pg_dump &> /dev/null; then
        log_error "pg_dump 未安装"
        exit 1
    fi
    
    if ! command -v gzip &> /dev/null; then
        log_error "gzip 未安装"
        exit 1
    fi
    
    log_info "✅ 备份要求检查通过"
}

# 创建备份目录
create_backup_dir() {
    if [ ! -d "$BACKUP_DIR" ]; then
        mkdir -p "$BACKUP_DIR"
        log_info "创建备份目录: $BACKUP_DIR"
    fi
}

# 执行数据库备份
perform_backup() {
    log_info "开始备份数据库: $DB_NAME"
    
    # 设置 PostgreSQL 密码
    export PGPASSWORD="$DB_PASSWORD"
    
    # 执行备份
    if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        --verbose --no-owner --no-privileges --clean --if-exists \
        > "$BACKUP_DIR/$BACKUP_FILE"; then
        
        log_info "✅ 数据库备份完成: $BACKUP_FILE"
        
        # 压缩备份文件
        if gzip "$BACKUP_DIR/$BACKUP_FILE"; then
            log_info "✅ 备份文件已压缩: $COMPRESSED_FILE"
        else
            log_warn "备份文件压缩失败"
        fi
    else
        log_error "数据库备份失败"
        exit 1
    fi
    
    # 清除密码环境变量
    unset PGPASSWORD
}

# 验证备份文件
verify_backup() {
    local backup_path="$BACKUP_DIR/$COMPRESSED_FILE"
    
    if [ -f "$backup_path" ]; then
        local file_size=$(stat -c%s "$backup_path" 2>/dev/null || stat -f%z "$backup_path" 2>/dev/null)
        
        if [ "$file_size" -gt 1024 ]; then  # 文件大于 1KB
            log_info "✅ 备份文件验证通过 (大小: ${file_size} 字节)"
        else
            log_error "备份文件太小，可能备份失败"
            exit 1
        fi
    else
        log_error "备份文件不存在"
        exit 1
    fi
}

# 上传到云存储 (可选)
upload_to_cloud() {
    if [ -n "$BACKUP_S3_BUCKET" ] && command -v aws &> /dev/null; then
        log_info "上传备份到 S3..."
        
        local s3_path="s3://$BACKUP_S3_BUCKET/database-backups/$COMPRESSED_FILE"
        
        if aws s3 cp "$BACKUP_DIR/$COMPRESSED_FILE" "$s3_path"; then
            log_info "✅ 备份已上传到 S3: $s3_path"
        else
            log_warn "S3 上传失败"
        fi
    else
        log_info "跳过云存储上传 (未配置或 AWS CLI 不可用)"
    fi
}

# 清理旧备份
cleanup_old_backups() {
    log_info "清理 $RETENTION_DAYS 天前的备份文件..."
    
    # 清理本地备份
    find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
    
    # 清理 S3 备份 (如果配置了)
    if [ -n "$BACKUP_S3_BUCKET" ] && command -v aws &> /dev/null; then
        local cutoff_date=$(date -d "$RETENTION_DAYS days ago" +%Y%m%d 2>/dev/null || date -v-${RETENTION_DAYS}d +%Y%m%d 2>/dev/null)
        
        aws s3 ls "s3://$BACKUP_S3_BUCKET/database-backups/" | \
        awk '{print $4}' | \
        grep "backup_" | \
        while read file; do
            local file_date=$(echo "$file" | sed 's/backup_\([0-9]\{8\}\).*/\1/')
            if [ "$file_date" -lt "$cutoff_date" ]; then
                aws s3 rm "s3://$BACKUP_S3_BUCKET/database-backups/$file"
                log_info "删除旧的 S3 备份: $file"
            fi
        done
    fi
    
    log_info "✅ 旧备份清理完成"
}

# 发送通知
send_notification() {
    local status=$1
    local message="数据库备份${status}: 时间=${TIMESTAMP}, 文件=${COMPRESSED_FILE}"
    
    # Slack 通知
    if [ -n "$SLACK_WEBHOOK" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"$message\"}" \
            "$SLACK_WEBHOOK" 2>/dev/null || true
    fi
    
    # 邮件通知 (如果配置了)
    if [ -n "$ALERT_EMAIL" ] && command -v mail &> /dev/null; then
        echo "$message" | mail -s "数据库备份通知" "$ALERT_EMAIL" 2>/dev/null || true
    fi
    
    log_info "通知已发送: $message"
}

# 主备份流程
main() {
    log_info "开始数据库备份流程..."
    
    check_requirements
    create_backup_dir
    perform_backup
    verify_backup
    upload_to_cloud
    cleanup_old_backups
    
    send_notification "成功"
    log_info "🎉 数据库备份流程完成！"
}

# 错误处理
trap 'log_error "备份过程中发生错误"; send_notification "失败"; exit 1' ERR

# 显示帮助信息
show_help() {
    echo "数据库备份脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示帮助信息"
    echo "  --dry-run      模拟运行，不执行实际备份"
    echo ""
    echo "环境变量:"
    echo "  DB_NAME        数据库名称 (默认: daoist_video_db)"
    echo "  DB_USER        数据库用户 (默认: postgres)"
    echo "  DB_PASSWORD    数据库密码"
    echo "  DB_HOST        数据库主机 (默认: localhost)"
    echo "  DB_PORT        数据库端口 (默认: 5432)"
    echo "  BACKUP_DIR     备份目录 (默认: ./backups)"
    echo "  RETENTION_DAYS 保留天数 (默认: 30)"
    echo "  BACKUP_S3_BUCKET S3 存储桶名称 (可选)"
    echo "  SLACK_WEBHOOK  Slack 通知 URL (可选)"
    echo "  ALERT_EMAIL    告警邮箱 (可选)"
}

# 处理命令行参数
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    --dry-run)
        log_info "模拟运行模式"
        check_requirements
        create_backup_dir
        log_info "模拟运行完成，实际备份未执行"
        exit 0
        ;;
    "")
        main
        ;;
    *)
        log_error "未知参数: $1"
        show_help
        exit 1
        ;;
esac