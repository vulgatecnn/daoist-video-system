# 道教经文视频系统 - 服务启动脚本 (PowerShell版本)
# 使用方法: 右键点击 -> 使用 PowerShell 运行

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   道教经文视频系统 - 服务启动脚本" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查环境
Write-Host "[1/4] 检查环境..." -ForegroundColor Green

try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python 未安装或未添加到 PATH" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}

try {
    $nodeVersion = node --version 2>&1
    Write-Host "✅ Node.js: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Node.js 未安装或未添加到 PATH" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}

Write-Host ""

# 清理端口占用
Write-Host "[2/4] 清理端口占用..." -ForegroundColor Green

# 清理端口函数
function Clear-Port {
    param([int]$Port, [string]$ServiceName)
    
    Write-Host "检查端口 $Port ($ServiceName)..." -ForegroundColor Yellow
    $portUsage = netstat -ano | findstr ":$Port"
    
    if ($portUsage) {
        Write-Host "端口 $Port 被占用，正在清理..." -ForegroundColor Yellow
        $pids = ($portUsage | ForEach-Object { ($_ -split '\s+')[-1] }) | Sort-Object -Unique
        
        foreach ($processId in $pids) {
            if ($processId -and $processId -ne "0") {
                try {
                    Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
                    Write-Host "✅ 已清理进程 PID: $processId" -ForegroundColor Green
                } catch {
                    Write-Host "⚠️  无法停止进程 $processId" -ForegroundColor Yellow
                }
            }
        }
    } else {
        Write-Host "✅ 端口 $Port 可用" -ForegroundColor Green
    }
}

# 清理后端和前端端口
Clear-Port -Port 6000 -ServiceName "后端"
Clear-Port -Port 5500 -ServiceName "前端"

Write-Host ""

# 启动后端
Write-Host "[3/4] 启动后端服务..." -ForegroundColor Green
$backendPath = Join-Path $PSScriptRoot "backend"
if (Test-Path $backendPath) {
    Write-Host "启动 Django 开发服务器 (端口 6000)..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$backendPath'; python manage.py runserver 6000" -WindowStyle Normal
    Write-Host "✅ 后端服务启动中..." -ForegroundColor Green
} else {
    Write-Host "❌ 后端目录不存在: $backendPath" -ForegroundColor Red
}

Write-Host ""

# 启动前端
Write-Host "[4/4] 启动前端服务..." -ForegroundColor Green
$frontendPath = Join-Path $PSScriptRoot "frontend"
if (Test-Path $frontendPath) {
    Write-Host "启动 React 开发服务器 (端口 5500)..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$frontendPath'; `$env:PORT=5500; npm start" -WindowStyle Normal
    Write-Host "✅ 前端服务启动中..." -ForegroundColor Green
} else {
    Write-Host "❌ 前端目录不存在: $frontendPath" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🎉 服务启动完成！" -ForegroundColor Green
Write-Host ""
Write-Host "📋 服务信息：" -ForegroundColor Yellow
Write-Host "  后端 API：  http://localhost:6000/" -ForegroundColor White
Write-Host "  管理后台：  http://localhost:6000/admin/" -ForegroundColor White
Write-Host "  前端应用：  http://localhost:5500/" -ForegroundColor White
Write-Host ""
Write-Host "💡 提示：" -ForegroundColor Yellow
Write-Host "  - 两个服务会在新的 PowerShell 窗口中运行" -ForegroundColor White
Write-Host "  - 关闭对应窗口即可停止服务" -ForegroundColor White
Write-Host "  - 首次启动前端可能需要较长时间编译" -ForegroundColor White
Write-Host "  - 如需停止所有服务，请运行 停止服务.ps1" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Read-Host "按回车键退出"