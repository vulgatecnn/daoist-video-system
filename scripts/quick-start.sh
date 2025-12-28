#!/bin/bash

# 快速启动脚本
# 一键设置和启动道教视频系统的 CI/CD 环境

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
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 显示欢迎信息
show_welcome() {
    echo -e "${BLUE}"
    echo "=================================================="
    echo "    道教视频系统 CI/CD 快速启动脚本"
    echo "=================================================="
    echo -e "${NC}"
    echo "本脚本将帮助您快速设置和启动完整的 CI/CD 环境"
    echo ""
}

# 检查系统要求
check_requirements() {
    log_step "检查系统要求..."
    
    local missing_tools=()
    
    # 检查必要工具
    if ! command -v docker &> /dev/null; then
        missing_tools+=("docker")
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        missing_tools+=("docker-compose")
    fi
    
    if ! command -v git &> /dev/null; then
        missing_tools+=("git")
    fi
    
    if ! command -v curl &> /dev/null; then
        missing_tools+=("curl")
    fi
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        log_error "缺少必要工具: ${missing_tools[*]}"
        log_info "请先安装这些工具后再运行此脚本"
        exit 1
    fi
    
    log_info "✅ 系统要求检查通过"
}

# 设置环境变量
setup_environment() {
    log_step "设置环境变量..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log_info "✅ 已创建 .env 文件"
            log_warn "请编辑 .env 文件并填入正确的配置值"
        else
            log_error ".env.example 文件不存在"
            exit 1
        fi
    else
        log_info "✅ .env 文件已存在"
    fi
}

# 设置权限
setup_permissions() {
    log_step "设置文件权限..."
    
    if [ -f "scripts/setup-permissions.sh" ]; then
        chmod +x scripts/setup-permissions.sh
        ./scripts/setup-permissions.sh
    else
        log_error "权限设置脚本不存在"
        exit 1
    fi
}

# 构建镜像
build_images() {
    log_step "构建 Docker 镜像..."
    
    log_info "构建开发环境镜像..."
    docker-compose build
    
    log_info "✅ 镜像构建完成"
}

# 启动基础服务
start_basic_services() {
    log_step "启动基础服务..."
    
    # 启动数据库和缓存
    docker-compose up -d db redis
    
    # 等待数据库启动
    log_info "等待数据库启动..."
    sleep 10
    
    # 运行数据库迁移
    log_info "运行数据库迁移..."
    docker-compose run --rm backend python manage.py migrate
    
    # 收集静态文件
    log_info "收集静态文件..."
    docker-compose run --rm backend python manage.py collectstatic --noinput
    
    # 启动所有服务
    docker-compose up -d
    
    log_info "✅ 基础服务启动完成"
}

# 启动监控服务
start_monitoring() {
    log_step "启动监控服务..."
    
    if [ -f "docker-compose.monitoring.yml" ]; then
        docker-compose -f docker-compose.monitoring.yml up -d
        log_info "✅ 监控服务启动完成"
    else
        log_warn "监控配置文件不存在，跳过监控服务启动"
    fi
}

# 验证服务状态
verify_services() {
    log_step "验证服务状态..."
    
    local max_attempts=30
    local attempt=1
    
    log_info "等待服务启动..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:8000/health/ > /dev/null 2>&1; then
            log_info "✅ 后端服务健康检查通过"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            log_error "❌ 后端服务启动失败"
            return 1
        fi
        
        echo -n "."
        sleep 2
        ((attempt++))
    done
    
    # 检查前端服务
    if curl -f http://localhost/ > /dev/null 2>&1; then
        log_info "✅ 前端服务健康检查通过"
    else
        log_warn "⚠️  前端服务可能未正常启动"
    fi
    
    # 检查监控服务
    if curl -f http://localhost:3000 > /dev/null 2>&1; then
        log_info "✅ Grafana 监控面板可访问"
    else
        log_warn "⚠️  监控服务可能未启动"
    fi
}

# 显示访问信息
show_access_info() {
    log_step "服务访问信息"
    
    echo ""
    echo -e "${GREEN}🎉 道教视频系统已成功启动！${NC}"
    echo ""
    echo "📱 应用服务:"
    echo "  前端应用: http://localhost"
    echo "  后端 API: http://localhost:8000"
    echo "  健康检查: http://localhost:8000/health/"
    echo ""
    echo "📊 监控服务:"
    echo "  Grafana:     http://localhost:3000 (admin/admin)"
    echo "  Prometheus:  http://localhost:9090"
    echo "  Alertmanager: http://localhost:9093"
    echo ""
    echo "🗄️ 数据库服务:"
    echo "  PostgreSQL: localhost:5432"
    echo "  Redis:      localhost:6379"
    echo ""
    echo "📋 管理命令:"
    echo "  查看日志:   docker-compose logs -f"
    echo "  停止服务:   docker-compose down"
    echo "  重启服务:   docker-compose restart"
    echo ""
    echo "📚 更多信息请查看: CI-CD-COMPLETE-GUIDE.md"
    echo ""
}

# 创建管理员用户
create_admin_user() {
    log_step "创建管理员用户..."
    
    echo ""
    read -p "是否创建管理员用户? (y/n): " create_admin
    
    if [ "$create_admin" = "y" ] || [ "$create_admin" = "Y" ]; then
        echo "请输入管理员信息:"
        read -p "用户名: " admin_username
        read -p "邮箱: " admin_email
        
        docker-compose exec backend python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='$admin_username').exists():
    User.objects.create_superuser('$admin_username', '$admin_email', 'admin123')
    print('管理员用户创建成功')
else:
    print('用户已存在')
"
        
        log_info "✅ 管理员用户设置完成"
        log_warn "默认密码: admin123 (请及时修改)"
    fi
}

# 运行初始化测试
run_initial_tests() {
    log_step "运行初始化测试..."
    
    echo ""
    read -p "是否运行初始化测试? (y/n): " run_tests
    
    if [ "$run_tests" = "y" ] || [ "$run_tests" = "Y" ]; then
        log_info "运行后端测试..."
        docker-compose exec backend python manage.py test --verbosity=2
        
        log_info "运行前端测试..."
        docker-compose exec frontend npm test -- --watchAll=false
        
        log_info "✅ 初始化测试完成"
    fi
}

# 设置开发工具
setup_dev_tools() {
    log_step "设置开发工具..."
    
    echo ""
    read -p "是否安装开发工具? (y/n): " install_tools
    
    if [ "$install_tools" = "y" ] || [ "$install_tools" = "Y" ]; then
        # 安装 pre-commit hooks
        if command -v pre-commit &> /dev/null; then
            pre-commit install
            log_info "✅ Pre-commit hooks 已安装"
        else
            log_warn "pre-commit 未安装，跳过 hooks 设置"
        fi
        
        # 设置 Git hooks
        if [ -d ".git" ]; then
            echo "#!/bin/bash" > .git/hooks/pre-push
            echo "echo '运行测试...'" >> .git/hooks/pre-push
            echo "docker-compose exec -T backend python manage.py test" >> .git/hooks/pre-push
            chmod +x .git/hooks/pre-push
            log_info "✅ Git pre-push hook 已设置"
        fi
    fi
}

# 显示下一步建议
show_next_steps() {
    echo ""
    echo -e "${BLUE}📋 下一步建议:${NC}"
    echo ""
    echo "1. 📝 编辑 .env 文件，配置生产环境参数"
    echo "2. 🔑 运行 ./scripts/setup-secrets.sh 设置 GitHub Secrets"
    echo "3. 🚀 推送代码到 GitHub 触发 CI/CD 流程"
    echo "4. 📊 访问 Grafana 配置监控面板"
    echo "5. 🧪 运行性能测试: ./performance/run-performance-tests.sh"
    echo "6. 💾 设置定期备份: crontab -e"
    echo ""
    echo -e "${GREEN}🎯 快速启动完成！祝您使用愉快！${NC}"
}

# 错误处理
handle_error() {
    log_error "快速启动过程中发生错误"
    log_info "请检查错误信息并重试"
    log_info "如需帮助，请查看 CI-CD-COMPLETE-GUIDE.md"
    exit 1
}

# 主函数
main() {
    show_welcome
    
    check_requirements
    setup_environment
    setup_permissions
    build_images
    start_basic_services
    start_monitoring
    verify_services
    
    show_access_info
    create_admin_user
    run_initial_tests
    setup_dev_tools
    show_next_steps
}

# 显示帮助信息
show_help() {
    echo "道教视频系统 CI/CD 快速启动脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示帮助信息"
    echo "  --no-build     跳过镜像构建"
    echo "  --no-monitor   跳过监控服务启动"
    echo "  --dev-only     仅启动开发环境"
    echo ""
    echo "功能:"
    echo "  - 检查系统要求"
    echo "  - 设置环境变量和权限"
    echo "  - 构建和启动所有服务"
    echo "  - 验证服务状态"
    echo "  - 创建管理员用户"
    echo "  - 运行初始化测试"
}

# 处理命令行参数
NO_BUILD=false
NO_MONITOR=false
DEV_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        --no-build)
            NO_BUILD=true
            shift
            ;;
        --no-monitor)
            NO_MONITOR=true
            shift
            ;;
        --dev-only)
            DEV_ONLY=true
            shift
            ;;
        *)
            log_error "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
done

# 错误处理
trap handle_error ERR

# 执行主函数
main