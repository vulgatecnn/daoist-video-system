@echo off
chcp 65001 >nul
echo ========================================
echo    道教经文视频系统 - 服务停止脚本
echo ========================================
echo.

echo [1/2] 停止后端服务...
echo 查找并停止 Django 进程...
for /f "tokens=2" %%i in ('tasklist /fi "windowtitle eq Django后端服务*" /fo table /nh 2^>nul') do (
    if not "%%i"=="INFO:" (
        taskkill /pid %%i /f >nul 2>&1
        echo ✅ Django 服务已停止 (PID: %%i)
    )
)

echo 停止 Python manage.py runserver 进程...
taskkill /f /im python.exe /fi "commandline eq *manage.py runserver*" >nul 2>&1

echo.

echo [2/2] 停止前端服务...
echo 查找并停止 React 进程...
for /f "tokens=2" %%i in ('tasklist /fi "windowtitle eq React前端服务*" /fo table /nh 2^>nul') do (
    if not "%%i"=="INFO:" (
        taskkill /pid %%i /f >nul 2>&1
        echo ✅ React 服务已停止 (PID: %%i)
    )
)

echo 停止 Node.js 开发服务器进程...
taskkill /f /im node.exe /fi "commandline eq *react-scripts*" >nul 2>&1

echo.
echo ========================================
echo 🛑 所有服务已停止
echo ========================================
echo.
pause