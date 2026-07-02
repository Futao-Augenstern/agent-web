@echo off
chcp 65001 >nul
title 我的专属 AI 智能体 v2.0

echo ============================================
echo    我的专属 AI 智能体 v2.0
echo    工作流: 写周报 | 学知识 | 改代码
echo    功能: 流式输出 | 对话历史 | 知识库
echo ============================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未找到 Python，请先安装 Python
    pause
    exit /b 1
)

pip show openai >nul 2>&1
if %errorlevel% neq 0 (
    echo 正在安装 openai 库...
    pip install openai
    echo.
)

echo 正在启动智能体服务...
echo 服务地址: http://127.0.0.1:8765/
echo 按 Ctrl+C 停止服务
echo.

python agent.py

pause
