#!/bin/bash

# 权限设置脚本
# 为CI/CD流程设置正确的文件和目录权限

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

# 检查是否为 root 用户
check_root() {
    if [ "$EUID" -eq 0 ]; then
        log_warn "正在以 root 用户运行，请确保这是必要的"
    fi
}

# 设置脚本执行权限
set_script_permissions() {
    log_info "设置脚本执行权限..."
    
    # 部署相关脚本
    chmod +x scripts/deploy.sh
    chmod +x scripts/backup-database.sh
    chmod +x scripts/restore-database.sh
    chmod +x scripts/rollback.sh
    chmod +x scripts/setup-secrets.sh
    
    # 性能测试脚本
    chmod +x performance/run-performance-tests.sh
    
    # 启动脚本
    chmod +x startup.bat
    chmod +x 停止服务.bat
    chmod +x 停止服务.ps1
    chmod +x 启动服务.ps1
    
    log_info "✅ 脚本权限设置完成"
}

# 设置目录权限
set_directory_permissions() {
    log_info "设置目录权限..."
    
    # 创建必要的目录
    mkdir -p backups
    mkdir -p logs
    mkdir -p media
    mkdir -p performance/reports
    mkdir -p monitoring/data
    
    # 设置目录权限
    chmod 755 backups
    chmod 755 logs
    chmod 755 media
    chmod 755 performance/reports
    chmod 755 monitoring/data
    
    # 设置备份目录权限 (更严格)
    chmod 750 backups
    
    log_info "✅ 目录权限设置完成"
}

# 设置配置文件权限
set_config_permissions() {
    log_info "设置配置文件权限..."
    
    # 环境变量文件 (敏感信息)
    if [ -f ".env" ]; then
        chmod 600 .env
        log_info "✅ .env 文件权限设置为 600"
    fi
    
    # Docker Compose 文件
    chmod 644 docker-compose*.yml
    
    # Nginx 配置文件
    if [ -d "nginx" ]; then
        chmod 644 nginx/*.conf
    fi
    
    # 监控配置文件
    if [ -d "monitoring" ]; then
        chmod 644 monitoring/*.yml
        chmod 644 monitoring/*.yaml
    fi
    
    log_info "✅ 配置文件权限设置完成"
}

# 设置 SSH 密钥权限
set_ssh_permissions() {
    log_info "检查 SSH 密钥权限..."
    
    # 检查 ~/.ssh 目录
    if [ -d "$HOME/.ssh" ]; then
        chmod 700 "$HOME/.ssh"
        
        # 设置私钥权限
        find "$HOME/.ssh" -name "id_*" -not -name "*.pub" -exec chmod 600 {} \;
        
        # 设置公钥权限
        find "$HOME/.ssh" -name "*.pub" -exec chmod 644 {} \;
        
        # 设置 authorized_keys 权限
        if [ -f "$HOME/.ssh/authorized_keys" ]; then
            chmod 600 "$HOME/.ssh/authorized_keys"
        fi
        
        # 设置 known_hosts 权限
        if [ -f "$HOME/.ssh/known_hosts" ]; then
            chmod 644 "$HOME/.ssh/known_hosts"
        fi
        
        log_info "✅ SSH 密钥权限设置完成"
    else
        log_warn "未找到 ~/.ssh 目录"
    fi
}

# 设置 Docker 权限
set_docker_permissions() {
    log_info "设置 Docker 权限..."
    
    # 检查当前用户是否在 docker 组中
    if groups "$USER" | grep -q docker; then
        log_info "✅ 用户 $USER 已在 docker 组中"
    else
        log_warn "用户 $USER 不在 docker 组中"
        log_info "请运行以下命令将用户添加到 docker 组:"
        log_info "sudo usermod -aG docker $USER"
        log_info "然后重新登录或运行: newgrp docker"
    fi
    
    # 检查 Docker socket 权限
    if [ -S "/var/run/docker.sock" ]; then
        local socket_perms=$(stat -c "%a" /var/run/docker.sock)
        if [ "$socket_perms" = "660" ] || [ "$socket_perms" = "666" ]; then
            log_info "✅ Docker socket 权限正确: $socket_perms"
        else
            log_warn "Docker socket 权限可能不正确: $socket_perms"
        fi
    fi
}

# 设置日志文件权限
set_log_permissions() {
    log_info "设置日志文件权限..."
    
    # 创建日志目录
    mkdir -p logs
    mkdir -p backend/logs
    
    # 设置日志目录权限
    chmod 755 logs
    chmod 755 backend/logs
    
    # 设置现有日志文件权限
    find logs -name "*.log" -exec chmod 644 {} \; 2>/dev/null || true
    find backend/logs -name "*.log" -exec chmod 644 {} \; 2>/dev/null || true
    
    log_info "✅ 日志文件权限设置完成"
}

# 设置媒体文件权限
set_media_permissions() {
    log_info "设置媒体文件权限..."
    
    # 创建媒体目录
    mkdir -p media
    mkdir -p backend/media
    
    # 设置媒体目录权限
    chmod 755 media
    chmod 755 backend/media
    
    # 设置媒体文件权限
    find media -type f -exec chmod 644 {} \; 2>/dev/null || true
    find backend/media -type f -exec chmod 644 {} \; 2>/dev/null || true
    
    log_info "✅ 媒体文件权限设置完成"
}

# 设置 Git 权限
set_git_permissions() {
    log_info "设置 Git 权限..."
    
    if [ -d ".git" ]; then
        # 设置 .git 目录权限
        chmod 755 .git
        
        # 设置 Git hooks 权限
        if [ -d ".git/hooks" ]; then
            find .git/hooks -type f -exec chmod +x {} \; 2>/dev/null || true
        fi
        
        log_info "✅ Git 权限设置完成"
    else
        log_warn "当前目录不是 Git 仓库"
    fi
}

# 验证权限设置
verify_permissions() {
    log_info "验证权限设置..."
    
    local errors=0
    
    # 检查关键脚本是否可执行
    for script in scripts/deploy.sh scripts/backup-database.sh scripts/rollback.sh; do
        if [ -f "$script" ] && [ -x "$script" ]; then
            log_info "✅ $script 可执行"
        else
            log_error "❌ $script 不可执行"
            ((errors++))
        fi
    done
    
    # 检查 .env 文件权限
    if [ -f ".env" ]; then
        local env_perms=$(stat -c "%a" .env)
        if [ "$env_perms" = "600" ]; then
            log_info "✅ .env 文件权限正确"
        else
            log_warn "⚠️  .env 文件权限: $env_perms (建议: 600)"
        fi
    fi
    
    # 检查备份目录权限
    if [ -d "backups" ]; then
        local backup_perms=$(stat -c "%a" backups)
        if [ "$backup_perms" = "750" ] || [ "$backup_perms" = "755" ]; then
            log_info "✅ 备份目录权限正确"
        else
            log_warn "⚠️  备份目录权限: $backup_perms"
        fi
    fi
    
    if [ $errors -eq 0 ]; then
        log_info "✅ 权限验证通过"
    else
        log_error "❌ 发现 $errors 个权限问题"
        return 1
    fi
}

# 生成权限报告
generate_permissions_report() {
    log_info "生成权限报告..."
    
    local report_file="permissions_report_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "权限设置报告"
        echo "生成时间: $(date)"
        echo "用户: $USER"
        echo "工作目录: $(pwd)"
        echo ""
        
        echo "=== 脚本权限 ==="
        find scripts -name "*.sh" -exec ls -la {} \; 2>/dev/null || echo "未找到脚本目录"
        echo ""
        
        echo "=== 配置文件权限 ==="
        ls -la *.yml *.yaml .env 2>/dev/null || echo "未找到配置文件"
        echo ""
        
        echo "=== 目录权限 ==="
        ls -la backups logs media 2>/dev/null || echo "未找到相关目录"
        echo ""
        
        echo "=== Docker 组成员 ==="
        groups "$USER" | grep docker || echo "用户不在 docker 组中"
        echo ""
        
        echo "=== SSH 权限 ==="
        ls -la "$HOME/.ssh/" 2>/dev/null || echo "未找到 SSH 目录"
        
    } > "$report_file"
    
    log_info "✅ 权限报告已生成: $report_file"
}

# 主函数
main() {
    log_info "开始设置 CI/CD 权限..."
    
    check_root
    set_script_permissions
    set_directory_permissions
    set_config_permissions
    set_ssh_permissions
    set_docker_permissions
    set_log_permissions
    set_media_permissions
    set_git_permissions
    
    if verify_permissions; then
        generate_permissions_report
        log_info "🎉 权限设置完成！"
    else
        log_error "💥 权限设置过程中发现问题"
        exit 1
    fi
}

# 显示帮助信息
show_help() {
    echo "CI/CD 权限设置脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示帮助信息"
    echo "  -v, --verify   仅验证权限，不修改"
    echo "  -r, --report   生成权限报告"
    echo ""
    echo "功能:"
    echo "  - 设置脚本执行权限"
    echo "  - 设置目录和文件权限"
    echo "  - 配置 SSH 密钥权限"
    echo "  - 检查 Docker 权限"
    echo "  - 验证权限设置"
}

# 处理命令行参数
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    -v|--verify)
        verify_permissions
        exit $?
        ;;
    -r|--report)
        generate_permissions_report
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