# 道教经文视频系统 - 服务停止脚本 (PowerShell版本)
# 使用方法: 右键点击 -> 使用 PowerShell 运行

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   道教经文视频系统 - 服务停止脚本" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 停止后端服务
Write-Host "[1/2] 停止后端服务..." -ForegroundColor Green

# 查找并停止 Django 进程
$djangoProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*manage.py runserver*"
}

if ($djangoProcesses) {
    foreach ($process in $djangoProcesses) {
        try {
            Stop-Process -Id $process.Id -Force
            Write-Host "✅ Django 服务已停止 (PID: $($process.Id))" -ForegroundColor Green
        } catch {
            Write-Host "⚠️  无法停止进程 $($process.Id): $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "ℹ️  未找到运行中的 Django 服务" -ForegroundColor Blue
}

Write-Host ""

# 停止前端服务
Write-Host "[2/2] 停止前端服务..." -ForegroundColor Green

# 查找并停止 Node.js 进程
$nodeProcesses = Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*react-scripts*"
}

if ($nodeProcesses) {
    foreach ($process in $nodeProcesses) {
        try {
            Stop-Process -Id $process.Id -Force
            Write-Host "✅ React 服务已停止 (PID: $($process.Id))" -ForegroundColor Green
        } catch {
            Write-Host "⚠️  无法停止进程 $($process.Id): $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "ℹ️  未找到运行中的 React 服务" -ForegroundColor Blue
}

# 额外清理：停止可能的端口占用
Write-Host ""
Write-Host "🔍 检查端口占用..." -ForegroundColor Yellow

# 检查 6000 端口 (Django)
$port6000 = netstat -ano | findstr ":6000"
if ($port6000) {
    Write-Host "发现端口 6000 被占用，尝试释放..." -ForegroundColor Yellow
    $pids = ($port6000 | ForEach-Object { ($_ -split '\s+')[-1] }) | Sort-Object -Unique
    foreach ($processId in $pids) {
        if ($processId -and $processId -ne "0") {
            try {
                Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
                Write-Host "✅ 已释放端口 6000 (PID: $processId)" -ForegroundColor Green
            } catch {
                Write-Host "⚠️  无法停止进程 $processId" -ForegroundColor Yellow
            }
        }
    }
}

# 检查 5500 端口 (React)
$port5500 = netstat -ano | findstr ":5500"
if ($port5500) {
    Write-Host "发现端口 5500 被占用，尝试释放..." -ForegroundColor Yellow
    $pids = ($port5500 | ForEach-Object { ($_ -split '\s+')[-1] }) | Sort-Object -Unique
    foreach ($processId in $pids) {
        if ($processId -and $processId -ne "0") {
            try {
                Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
                Write-Host "✅ 已释放端口 5500 (PID: $processId)" -ForegroundColor Green
            } catch {
                Write-Host "⚠️  无法停止进程 $processId" -ForegroundColor Yellow
            }
        }
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🛑 所有服务已停止" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Read-Host "按回车键退出"