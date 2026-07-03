@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title 我的专属 AI 智能体 v2.0

:: ── 配置项 ────────────────────────────────────────────────────
set "PORT=8765"
set "HOST=127.0.0.1"
set "REQUIRED_PKGS=openai"

:: ── 启动横幅 ──────────────────────────────────────────────────
cls
echo.
echo    ╔══════════════════════════════════════════╗
echo    ║       我的专属 AI 智能体 v2.0            ║
echo    ╠══════════════════════════════════════════╣
echo    ║  工作流: 写周报 | 学知识 | 改代码        ║
echo    ║  功  能: 流式输出 | 对话历史 | 知识库     ║
echo    ╚══════════════════════════════════════════╝
echo.

:: ── 检查 Python ──────────────────────────────────────────────
echo [1/3] 检查运行环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ❌  未找到 Python，请先安装 Python 3.8+
    echo     下载地址: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set "PY_VER=%%v"
echo     ✓ Python %PY_VER%

:: ── 检查依赖 ──────────────────────────────────────────────────
echo [2/3] 检查依赖包...
set "MISSING="
for %%p in (%REQUIRED_PKGS%) do (
    pip show %%p >nul 2>&1
    if !errorlevel! neq 0 (
        set "MISSING=!MISSING! %%p"
    )
)

if defined MISSING (
    echo     需要安装:%MISSING%
    echo     正在安装...
    pip install %MISSING% >nul 2>&1
    if !errorlevel! neq 0 (
        echo.
        echo ❌  依赖安装失败，请检查网络连接
        echo     或手动运行: pip install openai
        echo.
        pause
        exit /b 1
    )
    echo     ✓ 依赖安装完成
) else (
    echo     ✓ 依赖已就绪
)

:: ── 检查 agent.py ────────────────────────────────────────────
if not exist "%~dp0agent.py" (
    echo.
    echo ❌  未找到 agent.py 文件，请确认在正确的目录下运行
    echo.
    pause
    exit /b 1
)

:: ── 启动服务 ──────────────────────────────────────────────────
echo [3/3] 启动智能体服务...
echo.
echo     🌐 服务地址: http://%HOST%:%PORT%/
echo     📖 API文档: http://%HOST%:%PORT%/api
echo     ⏹  停止服务: Ctrl + C
echo.
echo ============================================================
echo.

:: 自动打开浏览器（可选）
start "" "http://%HOST%:%PORT%/"

:: 启动服务
python "%~dp0agent.py"

:: 服务退出
set "EXIT_CODE=%errorlevel%"
echo.
echo ============================================================
if %EXIT_CODE% equ 0 (
    echo  服务已正常停止
) else (
    echo  服务异常退出 (错误码: %EXIT_CODE%)
)
echo.

endlocal
pause
