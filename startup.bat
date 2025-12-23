@echo off
chcp 65001 >nul
echo ========================================
echo    道教经文视频系统 - 服务启动脚本
echo ========================================
echo.

echo [1/3] 检查环境...
echo 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python 未安装或未添加到 PATH
    pause
    exit /b 1
)

echo 检查 Node.js 环境...
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js 未安装或未添加到 PATH
    pause
    exit /b 1
)

echo ✅ 环境检查完成
echo.

echo [2/4] 清理端口占用...
echo 检查并清理端口 8000 (后端)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do (
    echo 清理端口 8000 的进程 %%a
    taskkill /F /PID %%a >nul 2>&1
)

echo 检查并清理端口 3000 (前端)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000') do (
    echo 清理端口 3000 的进程 %%a
    taskkill /F /PID %%a >nul 2>&1
)
echo ✅ 端口清理完成
echo.

echo [3/4] 启动后端服务...
echo 启动 Django 开发服务器 (端口 8000)...
cd /d "%~dp0backend"
start "Django后端服务" cmd /k "python manage.py runserver 8000"
echo ✅ 后端服务启动中...
echo.

echo [4/4] 启动前端服务...
echo 启动 React 开发服务器 (端口 3000)...
cd /d "%~dp0frontend"
start "React前端服务" cmd /k "npm start"
echo ✅ 前端服务启动中...
echo.

echo ========================================
echo 🎉 服务启动完成！
echo.
echo 📋 服务信息：
echo   后端 API：  http://localhost:8000/
echo   管理后台：  http://localhost:8000/admin/
echo   前端应用：  http://localhost:3000/
echo.
echo 💡 提示：
echo   - 两个服务会在新的命令行窗口中运行
echo   - 关闭对应窗口即可停止服务
echo   - 首次启动前端可能需要较长时间编译
echo ========================================
echo.
pause