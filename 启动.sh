#!/bin/bash
# AI 智能体启动脚本 (Mac/Linux)

set -e

# 配置
PORT=8765
HOST=127.0.0.1
REQUIRED_PKGS="openai"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

clear
echo ""
echo "    ╔══════════════════════════════════════════╗"
echo "    ║       我的专属 AI 智能体 v2.0            ║"
echo "    ╠══════════════════════════════════════════╣"
echo "    ║  工作流: 写周报 | 学知识 | 改代码        ║"
echo "    ║  功  能: 流式输出 | 对话历史 | 知识库     ║"
echo "    ╚══════════════════════════════════════════╝"
echo ""

# 检查 Python
echo -e "${BLUE}[1/3]${NC} 检查运行环境..."
if ! command -v python3 &> /dev/null; then
    echo ""
    echo -e "${RED}❌  未找到 Python3，请先安装 Python 3.8+${NC}"
    echo "     下载地址: https://www.python.org/downloads/"
    echo ""
    exit 1
fi
PY_VER=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "     ${GREEN}✓${NC} Python $PY_VER"

# 检查依赖
echo -e "${BLUE}[2/3]${NC} 检查依赖包..."
MISSING=""
for pkg in $REQUIRED_PKGS; do
    if ! python3 -c "import $pkg" 2>/dev/null; then
        MISSING="$MISSING $pkg"
    fi
done

if [ -n "$MISSING" ]; then
    echo "     需要安装:$MISSING"
    echo "     正在安装..."
    if ! pip3 install $MISSING 2>/dev/null; then
        echo ""
        echo -e "${RED}❌  依赖安装失败，请检查网络连接${NC}"
        echo "     或手动运行: pip3 install openai"
        echo ""
        exit 1
    fi
    echo -e "     ${GREEN}✓${NC} 依赖安装完成"
else
    echo -e "     ${GREEN}✓${NC} 依赖已就绪"
fi

# 检查 agent.py
if [ ! -f "$SCRIPT_DIR/agent.py" ]; then
    echo ""
    echo -e "${RED}❌  未找到 agent.py 文件，请确认在正确的目录下运行${NC}"
    echo ""
    exit 1
fi

# 启动服务
echo -e "${BLUE}[3/3]${NC} 启动智能体服务..."
echo ""
echo "     🌐 服务地址: http://$HOST:$PORT/"
echo "     📖 API文档: http://$HOST:$PORT/api"
echo "     ⏹  停止服务: Ctrl + C"
echo ""
echo "============================================================"
echo ""

# 自动打开浏览器
if command -v open &> /dev/null; then
    open "http://$HOST:$PORT/"
elif command -v xdg-open &> /dev/null; then
    xdg-open "http://$HOST:$PORT/" 2>/dev/null &
fi

# 启动服务
python3 "$SCRIPT_DIR/agent.py"

EXIT_CODE=$?
echo ""
echo "============================================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "  服务已正常停止"
else
    echo -e "${RED}  服务异常退出 (错误码: $EXIT_CODE)${NC}"
fi
echo ""
