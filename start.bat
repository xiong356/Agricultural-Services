@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
title 溪山农服平台 - 后端 API 服务
color 0A

echo ============================================================
echo   溪山农服平台 - 后端 API 服务一键启动
echo ============================================================
echo.

:: --------------------------------------------------
:: Step 1: 检测可用的 Python
:: --------------------------------------------------
echo [1/4] 检测 Python 环境...

set "PYTHON_CMD="

:: 优先尝试系统 Python（3.12 兼容性最佳）
python --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_CMD=python"
    echo   ^> 找到系统 Python
    goto :found_python
)

:: 尝试 py launcher
py --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_CMD=py"
    echo   ^> 找到 py launcher
    goto :found_python
)

echo.
echo   [错误] 未找到 Python 环境！
echo   请安装 Python 3.10+ 后重试: https://www.python.org/downloads/
echo.
pause
exit /b 1

:found_python
echo.

:: --------------------------------------------------
:: Step 2: 创建虚拟环境（首次运行）
:: --------------------------------------------------
echo [2/4] 检查虚拟环境...

set "BACKEND_DIR=%~dp0backend"
set "VENV_DIR=%BACKEND_DIR%\venv"

if exist "%VENV_DIR%\Scripts\python.exe" (
    echo   ^> 虚拟环境已存在
    goto :venv_done
)

echo   ^> 首次运行，创建虚拟环境...
"%PYTHON_CMD%" -m venv "%VENV_DIR%"
if !errorlevel! neq 0 (
    echo   [错误] 虚拟环境创建失败
    pause
    exit /b 1
)
echo   ^> 虚拟环境创建成功

:venv_done
echo.

:: --------------------------------------------------
:: Step 3: 安装依赖
:: --------------------------------------------------
echo [3/4] 检查并安装依赖...

set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"

:: 检查 fastapi 是否已安装
"%VENV_PYTHON%" -c "import fastapi" >nul 2>&1
if !errorlevel! equ 0 (
    echo   ^> 依赖已就绪
    goto :deps_done
)

echo   ^> 安装依赖包...
"%VENV_PYTHON%" -m pip install -r "%BACKEND_DIR%\requirements.txt" -q
if !errorlevel! neq 0 (
    echo   [错误] 依赖安装失败，请检查网络连接
    pause
    exit /b 1
)
echo   ^> 依赖安装完成

:deps_done
echo.

:: --------------------------------------------------
:: Step 4: 启动服务器
:: --------------------------------------------------
echo [4/4] 启动后端服务...
echo.
echo ============================================================
echo.
echo   服务地址:  http://localhost:8000
echo   API 文档:  http://localhost:8000/docs
echo   健康检查:  http://localhost:8000/health
echo.
echo   前端 baseUrl 请修改为:
echo   http://localhost:8000/miniapp/v1
echo.
echo   按 Ctrl+C 停止服务
echo.
echo ============================================================
echo.

cd /d "%BACKEND_DIR%"
"%VENV_PYTHON%" app.py

echo.
echo 服务已停止。
pause
