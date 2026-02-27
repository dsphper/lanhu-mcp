#!/bin/bash

# 蓝湖 MCP Server - 超级简单安装脚本
# 专为小白用户设计，交互式引导安装

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# 清屏
clear

echo -e "${BOLD}${BLUE}"
echo "╔═══════════════════════════════════════════════════╗"
echo "║                                                   ║"
echo "║     🎨 蓝湖 MCP Server - 一键安装程序            ║"
echo "║                                                   ║"
echo "║     让 AI 助手共享团队知识，打破 AI IDE 孤岛     ║"
echo "║                                                   ║"
echo "╚═══════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo -e "${GREEN}欢迎！这个脚本会帮你自动完成所有安装步骤${NC}"
echo -e "${GREEN}预计耗时：3-5 分钟${NC}"
echo ""
echo -e "按 ${BOLD}Enter${NC} 开始安装，或按 ${BOLD}Ctrl+C${NC} 取消"
read

# ============================================
# 步骤 1: 环境检查
# ============================================

echo ""
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}📦 步骤 1/5: 检查系统环境${NC}"
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 检查 Python
echo -e "正在检查 Python..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ 未检测到 Python 3${NC}"
    echo ""
    echo "请先安装 Python 3.10 或更高版本："
    echo "  Mac: brew install python3"
    echo "  Ubuntu: sudo apt install python3 python3-pip"
    echo "  官网: https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo -e "${GREEN}✅ Python $PYTHON_VERSION${NC}"

# 检查 pip
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}❌ 未检测到 pip3${NC}"
    exit 1
fi
echo -e "${GREEN}✅ pip3 已安装${NC}"

# 检查 Git
if ! command -v git &> /dev/null; then
    echo -e "${YELLOW}⚠️  未检测到 Git（可选）${NC}"
else
    echo -e "${GREEN}✅ Git 已安装${NC}"
fi

echo ""
echo -e "${GREEN}🎉 环境检查通过！${NC}"
sleep 1

# ============================================
# 步骤 2: 安装依赖
# ============================================

echo ""
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}📥 步骤 2/5: 安装依赖包${NC}"
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo "正在创建 Python 虚拟环境..."
    python3 -m venv venv
    echo -e "${GREEN}✅ 虚拟环境创建完成${NC}"
else
    echo -e "${GREEN}✅ 虚拟环境已存在${NC}"
fi

# 激活虚拟环境
echo "正在激活虚拟环境..."
source venv/bin/activate

# 升级 pip
echo "正在升级 pip..."
pip install --upgrade pip -q

# 安装依赖
echo "正在安装项目依赖..."
echo -e "${YELLOW}（这可能需要 1-2 分钟，请耐心等待）${NC}"
pip install -r requirements.txt -q

echo -e "${GREEN}✅ 依赖安装完成${NC}"

# 安装 Playwright 浏览器
echo ""
echo "正在安装 Playwright 浏览器..."
echo -e "${YELLOW}（首次安装需要下载 Chromium，可能需要 1-2 分钟）${NC}"
playwright install chromium

echo ""
echo -e "${GREEN}🎉 依赖安装完成！${NC}"
sleep 1

# ============================================
# 步骤 3: 配置蓝湖 Cookie
# ============================================

echo ""
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}🍪 步骤 3/5: 配置蓝湖 Cookie${NC}"
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 复制 .env.example 到 .env
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}✅ 已创建 .env 配置文件${NC}"
    else
        echo -e "${RED}❌ 未找到 .env.example 文件${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ .env 文件已存在${NC}"
fi

echo ""
echo -e "${YELLOW}这是唯一需要你手动操作的步骤，很简单！${NC}"
echo ""
echo -e "${BOLD}请按照以下步骤操作：${NC}"
echo ""
echo -e "  1️⃣  在浏览器打开：${BOLD}${BLUE}https://lanhuapp.com${NC} 并登录"
echo ""
echo -e "  2️⃣  按下键盘 ${BOLD}F12${NC} 键（Mac 用户按 ${BOLD}Command+Option+I${NC}）"
echo "     会打开开发者工具"
echo ""
echo -e "  3️⃣  点击顶部的 ${BOLD}\"Network\"${NC}（网络）标签"
echo ""
echo -e "  4️⃣  按 ${BOLD}F5${NC} 刷新页面"
echo ""
echo -e "  5️⃣  在左侧请求列表中点击 ${BOLD}第一个请求${NC}"
echo ""
echo -e "  6️⃣  右侧找到 ${BOLD}\"Request Headers\"${NC} 部分"
echo "     找到 \"Cookie:\" 开头的那一行"
echo ""
echo -e "  7️⃣  ${BOLD}选中并复制${NC} 整个 Cookie 值"
echo "     （Cookie 很长，确保全部复制）"
echo ""
echo -e "  8️⃣  用文本编辑器打开当前目录下的 ${BOLD}.env${NC} 文件"
echo -e "     找到 ${BOLD}LANHU_COOKIE${NC} 这一行"
echo -e "     将 ${BOLD}your_lanhu_cookie_here${NC} 替换为你复制的 Cookie"
echo -e "     ${YELLOW}注意：保留引号，只替换引号内的内容${NC}"
echo ""
echo -e "${BOLD}${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 如果系统支持，尝试打开浏览器和文件
if command -v open &> /dev/null; then
    echo -e "我可以帮你打开蓝湖网站和 .env 文件吗？(y/n) [${BOLD}y${NC}]: "
    read -r open_files
    open_files=${open_files:-y}
    if [ "$open_files" = "y" ] || [ "$open_files" = "Y" ]; then
        open "https://lanhuapp.com" 2>/dev/null || true
        open -e ".env" 2>/dev/null || open ".env" 2>/dev/null || true
        echo -e "${GREEN}✅ 已打开浏览器和 .env 文件${NC}"
        echo ""
    fi
fi

echo -e "${BOLD}完成配置后，按 Enter 继续...${NC}"
read

# 读取 .env 文件中的 Cookie
if [ -f ".env" ]; then
    LANHU_COOKIE=$(grep "^LANHU_COOKIE=" .env | cut -d'"' -f2)
fi

# 验证 Cookie 不为空
if [ -z "$LANHU_COOKIE" ] || [ "$LANHU_COOKIE" = "your_lanhu_cookie_here" ]; then
    echo -e "${RED}❌ Cookie 未配置或配置不正确${NC}"
    echo -e "${YELLOW}请确保在 .env 文件中正确设置了 LANHU_COOKIE${NC}"
    exit 1
fi

# 简单验证 Cookie 格式
if [[ ! "$LANHU_COOKIE" =~ "session=" ]] && [[ ! "$LANHU_COOKIE" =~ "user_token=" ]]; then
    echo -e "${YELLOW}⚠️  Cookie 格式可能不正确${NC}"
    echo "确定要继续吗？(y/n) [n]: "
    read -r continue_anyway
    if [ "$continue_anyway" != "y" ] && [ "$continue_anyway" != "Y" ]; then
        echo "安装已取消"
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}✅ Cookie 配置验证通过！${NC}"
sleep 1

# ============================================
# 步骤 4: 创建数据目录
# ============================================

echo ""
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}📁 步骤 4/5: 创建数据目录${NC}"
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 创建数据目录
mkdir -p data logs
echo -e "${GREEN}✅ 数据目录已创建${NC}"

sleep 1

# ============================================
# 步骤 5: 启动服务
# ============================================

echo ""
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}🚀 步骤 5/5: 启动服务${NC}"
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${GREEN}是否现在启动服务？(y/n) [${BOLD}y${NC}]: ${NC}"
read -r start_now
start_now=${start_now:-y}

if [ "$start_now" = "y" ] || [ "$start_now" = "Y" ]; then
    echo ""
    echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${GREEN}🎉 安装成功！服务正在启动...${NC}"
    echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${BOLD}服务器地址：${NC}http://localhost:8000/mcp"
    echo ""
    echo -e "${BOLD}下一步：在 Cursor 中配置 MCP${NC}"
    echo ""
    echo "请将以下配置添加到 Cursor 的 MCP 配置文件中："
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    cat << 'MCP_CONFIG'
{
  "mcpServers": {
    "lanhu": {
      "url": "http://localhost:8000/mcp?role=Developer&name=YourName"
    }
  }
}
MCP_CONFIG
    echo -e "${YELLOW}提示：部分 AI 开发工具不支持 URL 中文参数，建议使用英文${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${BOLD}配置方法：${NC}"
    echo "  1. 打开 Cursor"
    echo "  2. 按 Command+Shift+P (Mac) 或 Ctrl+Shift+P (Windows)"
    echo "  3. 输入 'MCP' 找到 MCP 配置"
    echo "  4. 粘贴上面的配置"
    echo ""
    echo -e "按 ${BOLD}Ctrl+C${NC} 可以停止服务器"
    echo ""
    echo -e "${GREEN}正在启动服务器...${NC}"
    echo ""
    
    # 运行服务器
    python lanhu_mcp_server.py
else
    echo ""
    echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${GREEN}🎉 安装成功！${NC}"
    echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "稍后运行服务器，请执行："
    echo -e "  ${BOLD}source venv/bin/activate${NC}"
    echo -e "  ${BOLD}python lanhu_mcp_server.py${NC}"
    echo ""
fi

