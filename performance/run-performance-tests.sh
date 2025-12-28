#!/bin/bash

# 性能测试运行脚本
# 使用 Locust 进行自动化性能测试

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

# 默认配置
TARGET_HOST="${TARGET_HOST:-http://localhost:8000}"
USERS="${USERS:-50}"
SPAWN_RATE="${SPAWN_RATE:-5}"
RUN_TIME="${RUN_TIME:-300s}"
TEST_TYPE="${TEST_TYPE:-smoke}"
REPORT_DIR="./performance/reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 创建报告目录
mkdir -p "$REPORT_DIR"

# 检查依赖
check_requirements() {
    log_info "检查性能测试依赖..."
    
    if ! command -v locust &> /dev/null; then
        log_error "Locust 未安装，请运行: pip install locust"
        exit 1
    fi
    
    if ! command -v curl &> /dev/null; then
        log_error "curl 未安装"
        exit 1
    fi
    
    log_info "✅ 依赖检查通过"
}

# 检查目标服务是否可用
check_target_service() {
    log_info "检查目标服务: $TARGET_HOST"
    
    if curl -f "$TARGET_HOST/health/" > /dev/null 2>&1; then
        log_info "✅ 目标服务可用"
    else
        log_error "目标服务不可用，请检查服务状态"
        exit 1
    fi
}

# 运行冒烟测试
run_smoke_test() {
    log_info "运行冒烟测试..."
    
    local users=10
    local spawn_rate=2
    local run_time=60s
    local report_file="$REPORT_DIR/smoke_test_${TIMESTAMP}"
    
    locust -f performance/locustfile.py \
        --host="$TARGET_HOST" \
        --users="$users" \
        --spawn-rate="$spawn_rate" \
        --run-time="$run_time" \
        --headless \
        --html="${report_file}.html" \
        --csv="${report_file}" \
        --logfile="${report_file}.log" \
        --loglevel=INFO
    
    log_info "✅ 冒烟测试完成，报告: ${report_file}.html"
}

# 运行负载测试
run_load_test() {
    log_info "运行负载测试..."
    
    local report_file="$REPORT_DIR/load_test_${TIMESTAMP}"
    
    locust -f performance/locustfile.py \
        --host="$TARGET_HOST" \
        --users="$USERS" \
        --spawn-rate="$SPAWN_RATE" \
        --run-time="$RUN_TIME" \
        --headless \
        --html="${report_file}.html" \
        --csv="${report_file}" \
        --logfile="${report_file}.log" \
        --loglevel=INFO
    
    log_info "✅ 负载测试完成，报告: ${report_file}.html"
}

# 运行压力测试
run_stress_test() {
    log_info "运行压力测试..."
    
    local users=200
    local spawn_rate=10
    local run_time=600s
    local report_file="$REPORT_DIR/stress_test_${TIMESTAMP}"
    
    locust -f performance/locustfile.py \
        --host="$TARGET_HOST" \
        --users="$users" \
        --spawn-rate="$spawn_rate" \
        --run-time="$run_time" \
        --headless \
        --html="${report_file}.html" \
        --csv="${report_file}" \
        --logfile="${report_file}.log" \
        --loglevel=INFO
    
    log_info "✅ 压力测试完成，报告: ${report_file}.html"
}

# 运行峰值测试
run_spike_test() {
    log_info "运行峰值测试..."
    
    local report_file="$REPORT_DIR/spike_test_${TIMESTAMP}"
    
    # 阶段1: 正常负载
    log_info "阶段1: 正常负载 (50 用户)"
    locust -f performance/locustfile.py \
        --host="$TARGET_HOST" \
        --users=50 \
        --spawn-rate=5 \
        --run-time=120s \
        --headless \
        --csv="${report_file}_phase1" \
        --logfile="${report_file}_phase1.log" &
    
    wait
    
    # 阶段2: 峰值负载
    log_info "阶段2: 峰值负载 (300 用户)"
    locust -f performance/locustfile.py \
        --host="$TARGET_HOST" \
        --users=300 \
        --spawn-rate=20 \
        --run-time=180s \
        --headless \
        --csv="${report_file}_phase2" \
        --logfile="${report_file}_phase2.log" &
    
    wait
    
    # 阶段3: 恢复负载
    log_info "阶段3: 恢复负载 (50 用户)"
    locust -f performance/locustfile.py \
        --host="$TARGET_HOST" \
        --users=50 \
        --spawn-rate=5 \
        --run-time=120s \
        --headless \
        --html="${report_file}.html" \
        --csv="${report_file}_phase3" \
        --logfile="${report_file}_phase3.log"
    
    log_info "✅ 峰值测试完成，报告: ${report_file}.html"
}

# 分析测试结果
analyze_results() {
    local report_file="$1"
    
    if [ -f "${report_file}_stats.csv" ]; then
        log_info "分析测试结果..."
        
        # 提取关键指标
        local avg_response_time=$(tail -n 1 "${report_file}_stats.csv" | cut -d',' -f7)
        local max_response_time=$(tail -n 1 "${report_file}_stats.csv" | cut -d',' -f9)
        local failure_rate=$(tail -n 1 "${report_file}_stats.csv" | cut -d',' -f4)
        local rps=$(tail -n 1 "${report_file}_stats.csv" | cut -d',' -f10)
        
        echo "📊 测试结果摘要:"
        echo "  平均响应时间: ${avg_response_time}ms"
        echo "  最大响应时间: ${max_response_time}ms"
        echo "  失败率: ${failure_rate}%"
        echo "  每秒请求数: ${rps}"
        
        # 性能基准检查
        if (( $(echo "$avg_response_time > 2000" | bc -l) )); then
            log_warn "平均响应时间超过 2 秒基准"
        fi
        
        if (( $(echo "$failure_rate > 5" | bc -l) )); then
            log_warn "失败率超过 5% 基准"
        fi
    fi
}

# 生成性能报告
generate_report() {
    log_info "生成性能测试报告..."
    
    local summary_file="$REPORT_DIR/performance_summary_${TIMESTAMP}.md"
    
    cat > "$summary_file" << EOF
# 性能测试报告

**测试时间**: $(date)
**目标主机**: $TARGET_HOST
**测试类型**: $TEST_TYPE

## 测试配置

- 用户数: $USERS
- 生成速率: $SPAWN_RATE users/s
- 运行时间: $RUN_TIME

## 测试结果

详细结果请查看对应的 HTML 报告文件。

## 性能基准

- 平均响应时间: < 2000ms
- 95% 响应时间: < 5000ms
- 失败率: < 5%

## 建议

根据测试结果，建议关注以下方面：

1. 响应时间优化
2. 错误率降低
3. 系统稳定性提升

EOF

    log_info "✅ 性能报告生成: $summary_file"
}

# 清理旧报告
cleanup_old_reports() {
    log_info "清理 30 天前的旧报告..."
    
    find "$REPORT_DIR" -name "*.html" -mtime +30 -delete 2>/dev/null || true
    find "$REPORT_DIR" -name "*.csv" -mtime +30 -delete 2>/dev/null || true
    find "$REPORT_DIR" -name "*.log" -mtime +30 -delete 2>/dev/null || true
    
    log_info "✅ 旧报告清理完成"
}

# 发送通知
send_notification() {
    local status=$1
    local test_type=$2
    local message="性能测试${status}: 类型=${test_type}, 时间=$(date), 主机=${TARGET_HOST}"
    
    # Slack 通知
    if [ -n "$SLACK_WEBHOOK" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"$message\"}" \
            "$SLACK_WEBHOOK" 2>/dev/null || true
    fi
    
    log_info "通知已发送: $message"
}

# 主测试流程
main() {
    log_info "开始性能测试..."
    
    check_requirements
    check_target_service
    
    case "$TEST_TYPE" in
        smoke)
            run_smoke_test
            ;;
        load)
            run_load_test
            ;;
        stress)
            run_stress_test
            ;;
        spike)
            run_spike_test
            ;;
        all)
            run_smoke_test
            sleep 30
            run_load_test
            sleep 30
            run_stress_test
            ;;
        *)
            log_error "未知测试类型: $TEST_TYPE"
            exit 1
            ;;
    esac
    
    generate_report
    cleanup_old_reports
    send_notification "完成" "$TEST_TYPE"
    
    log_info "🎉 性能测试完成！"
}

# 显示帮助信息
show_help() {
    echo "性能测试脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help              显示帮助信息"
    echo "  -t, --type TYPE         测试类型 (smoke|load|stress|spike|all)"
    echo "  -u, --users USERS       用户数量 (默认: 50)"
    echo "  -r, --spawn-rate RATE   用户生成速率 (默认: 5)"
    echo "  -d, --duration TIME     运行时间 (默认: 300s)"
    echo "  --host HOST             目标主机 (默认: http://localhost:8000)"
    echo ""
    echo "示例:"
    echo "  $0 --type smoke"
    echo "  $0 --type load --users 100 --duration 600s"
    echo "  $0 --host https://api.example.com --type stress"
}

# 处理命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -t|--type)
            TEST_TYPE="$2"
            shift 2
            ;;
        -u|--users)
            USERS="$2"
            shift 2
            ;;
        -r|--spawn-rate)
            SPAWN_RATE="$2"
            shift 2
            ;;
        -d|--duration)
            RUN_TIME="$2"
            shift 2
            ;;
        --host)
            TARGET_HOST="$2"
            shift 2
            ;;
        *)
            log_error "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
done

# 错误处理
trap 'log_error "性能测试过程中发生错误"; send_notification "失败" "$TEST_TYPE"; exit 1' ERR

# 执行主函数
main