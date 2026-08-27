@echo off
chcp 65001 >nul 2>&1
echo 正在清理端口 8000...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000.*LISTENING"') do (
    echo 杀掉进程 PID: %%a
    taskkill /F /PID %%a >nul 2>&1
)

timeout /t 2 /nobreak >nul

netstat -ano | findstr ":8000.*LISTENING" >nul
if %errorlevel% neq 0 (
    echo 端口 8000 已释放！
) else (
    echo 仍有进程占用端口 8000，请手动打开任务管理器，搜索 python.exe 并结束所有进程
)

pause
