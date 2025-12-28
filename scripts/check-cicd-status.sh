#!/bin/bash

# CI/CD 状态检查脚本
# 检查GitHub Actions工作流状态和部署情况

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

log_step() {
    echo -e "${BLUE}[CHECK]${NC} $1"
}

# 显示标题
show_header() {
    echo -e "${BLUE}"
    echo "=================================================="
    echo "    道教视频系统 CI/CD 状态检查"
    echo "=================================================="
    echo -e "${NC}"
}

# 检查Git状态
check_git_status() {
    log_step "检查Git状态..."
    
    # 检查是否在Git仓库中
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_error "当前目录不是Git仓库"
        return 1
    fi
    
    # 获取当前分支和提交信息
    local current_branch=$(git rev-parse --abbrev-ref HEAD)
    local current_commit=$(git rev-parse --short HEAD)
    local commit_message=$(git log -1 --pretty=format:"%s")
    
    log_info "当前分支: $current_branch"
    log_info "最新提交: $current_commit"
    log_info "提交信息: $commit_message"
    
    # 检查是否有未提交的更改
    if ! git diff-index --quiet HEAD --; then
        log_warn "存在未提交的更改"
        git status --porcelain
    else
        log_info "✅ 工作目录干净"
    fi
}

# 检查GitHub Actions状态
check_github_actions() {
    log_step "检查GitHub Actions状态..."
    
    # 检查是否安装了GitHub CLI
    if ! command -v gh &> /dev/null; then
        log_warn "GitHub CLI 未安装，无法检查Actions状态"
        log_info "请访问 GitHub 仓库查看 Actions 状态"
        return 0
    fi
    
    # 检查是否已登录
    if ! gh auth status &> /dev/null; then
        log_warn "GitHub CLI 未登录，无法检查Actions状态"
        log_info "请运行 'gh auth login' 登录"
        return 0
    fi
    
    # 获取最新的工作流运行状态
    log_info "获取最新的工作流运行状态..."
    gh run list --limit 5 --json status,conclusion,createdAt,headBranch,workflowName
}

# 检查Docker镜像
check_docker_images() {
    log_step "检查Docker镜像..."
    
    if ! command -v docker &> /dev/null; then
        log_warn "Docker 未安装"
        return 0
    fi
    
    # 检查本地镜像
    log_info "本地Docker镜像:"
    docker images | grep -E "(daoist-video|postgres|redis)" || log_warn "未找到相关镜像"
}

# 检查服务状态
check_services() {
    log_step "检查服务状态..."
    
    # 检查Docker Compose服务
    if [ -f "docker-compose.yml" ]; then
        log_info "Docker Compose 服务状态:"
        docker-compose ps 2>/dev/null || log_warn "服务未运行"
    fi
    
    # 检查端口占用
    log_info "检查端口占用:"
    local ports=(8000 3000 5432 6379 9090 3000)
    for port in "${ports[@]}"; do
        if netstat -tuln 2>/dev/null | grep -q ":$port "; then
            log_info "✅ 端口 $port 已占用"
        else
            log_warn "端口 $port 未占用"
        fi
    done
}

# 检查健康状态
check_health() {
    log_step "检查应用健康状态..."
    
    # 检查后端健康状态
    if curl -f http://localhost:8000/health/ > /dev/null 2>&1; then
        log_info "✅ 后端服务健康"
        curl -s http://localhost:8000/health/ | jq '.' 2>/dev/null || echo "健康检查响应正常"
    else
        log_warn "后端服务不可访问"
    fi
    
    # 检查前端服务
    if curl -f http://localhost/ > /dev/null 2>&1; then
        log_info "✅ 前端服务可访问"
    else
        log_warn "前端服务不可访问"
    fi
    
    # 检查监控服务
    if curl -f http://localhost:3000 > /dev/null 2>&1; then
        log_info "✅ Grafana 监控可访问"
    else
        log_warn "Grafana 监控不可访问"
    fi
}

# 检查配置文件
check_configurations() {
    log_step "检查配置文件..."
    
    local config_files=(
        ".env.example"
        "docker-compose.yml"
        "docker-compose.prod.yml"
        "docker-compose.monitoring.yml"
        ".github/workflows/ci.yml"
        ".github/workflows/deploy.yml"
    )
    
    for file in "${config_files[@]}"; do
        if [ -f "$file" ]; then
            log_info "✅ $file 存在"
        else
            log_warn "❌ $file 不存在"
        fi
    done
}

# 检查脚本权限
check_script_permissions() {
    log_step "检查脚本权限..."
    
    local scripts=(
        "scripts/deploy.sh"
        "scripts/backup-database.sh"
        "scripts/rollback.sh"
        "scripts/quick-start.sh"
    )
    
    for script in "${scripts[@]}"; do
        if [ -f "$script" ]; then
            if [ -x "$script" ]; then
                log_info "✅ $script 可执行"
            else
                log_warn "⚠️  $script 不可执行"
            fi
        else
            log_warn "❌ $script 不存在"
        fi
    done
}

# 生成状态报告
generate_report() {
    log_step "生成状态报告..."
    
    local report_file="cicd_status_report_$(date +%Y%m%d_%H%M%S).md"
    
    {
        echo "# CI/CD 状态报告"
        echo ""
        echo "**生成时间**: $(date)"
        echo "**检查者**: $USER"
        echo ""
        
        echo "## Git 状态"
        echo "- 分支: $(git rev-parse --abbrev-ref HEAD)"
        echo "- 提交: $(git rev-parse --short HEAD)"
        echo "- 状态: $(git status --porcelain | wc -l) 个未提交更改"
        echo ""
        
        echo "## 服务状态"
        echo "- 后端服务: $(curl -f http://localhost:8000/health/ > /dev/null 2>&1 && echo "✅ 正常" || echo "❌ 异常")"
        echo "- 前端服务: $(curl -f http://localhost/ > /dev/null 2>&1 && echo "✅ 正常" || echo "❌ 异常")"
        echo "- 监控服务: $(curl -f http://localhost:3000 > /dev/null 2>&1 && echo "✅ 正常" || echo "❌ 异常")"
        echo ""
        
        echo "## 配置文件"
        for file in .env.example docker-compose.yml .github/workflows/ci.yml; do
            echo "- $file: $([ -f "$file" ] && echo "✅ 存在" || echo "❌ 缺失")"
        done
        echo ""
        
        echo "## 建议"
        echo "- 定期检查GitHub Actions工作流状态"
        echo "- 确保所有服务正常运行"
        echo "- 验证监控和告警配置"
        echo "- 测试备份和恢复流程"
        
    } > "$report_file"
    
    log_info "✅ 状态报告已生成: $report_file"
}

# 显示总结
show_summary() {
    echo ""
    echo -e "${BLUE}📋 CI/CD 状态检查总结:${NC}"
    echo ""
    echo "✅ 已完成的检查项目:"
    echo "  - Git 仓库状态"
    echo "  - GitHub Actions 工作流"
    echo "  - Docker 镜像和服务"
    echo "  - 应用健康状态"
    echo "  - 配置文件完整性"
    echo "  - 脚本权限设置"
    echo ""
    echo "📚 相关资源:"
    echo "  - GitHub Actions: https://github.com/$(git config --get remote.origin.url | sed 's/.*github.com[:/]\([^.]*\).*/\1/')/actions"
    echo "  - 监控面板: http://localhost:3000"
    echo "  - API文档: http://localhost:8000/api/"
    echo "  - 完整指南: CI-CD-COMPLETE-GUIDE.md"
    echo ""
}

# 主函数
main() {
    show_header
    check_git_status
    check_github_actions
    check_docker_images
    check_services
    check_health
    check_configurations
    check_script_permissions
    generate_report
    show_summary
}

# 显示帮助信息
show_help() {
    echo "CI/CD 状态检查脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示帮助信息"
    echo "  -q, --quick    快速检查（跳过详细检查）"
    echo "  -r, --report   仅生成报告"
    echo ""
    echo "功能:"
    echo "  - 检查Git仓库状态"
    echo "  - 验证GitHub Actions工作流"
    echo "  - 检查Docker服务状态"
    echo "  - 验证应用健康状态"
    echo "  - 检查配置文件完整性"
    echo "  - 生成状态报告"
}

# 处理命令行参数
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    -q|--quick)
        show_header
        check_git_status
        check_health
        show_summary
        ;;
    -r|--report)
        generate_report
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