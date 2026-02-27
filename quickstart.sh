#!/bin/bash
# 蓝湖 MCP 服务器快速启动脚本

set -e

echo "🎨 蓝湖 MCP 服务器 - 快速启动"
echo "=================================="
echo ""

# 检查 Python 版本
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误：未安装 Python 3"
    echo "请安装 Python 3.10 或更高版本"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Python 版本：$PYTHON_VERSION"

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo ""
    echo "📦 正在创建虚拟环境..."
    python3 -m venv venv
    echo "✅ 虚拟环境创建完成"
fi

# 激活虚拟环境
echo ""
echo "🔧 正在激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo ""
echo "📥 正在安装依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 安装 Playwright 浏览器
echo ""
echo "🌐 正在安装 Playwright 浏览器..."
playwright install chromium

# 检查 .env 是否存在
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  未找到配置文件 .env"
    
    if [ -f "config.example.env" ]; then
        echo "📝 正在从模板创建 .env..."
        cp config.example.env .env
        echo "✅ .env 文件已创建"
        echo ""
        echo "⚠️  重要提示：请编辑 .env 文件并设置你的 LANHU_COOKIE"
        echo "   1. 在编辑器中打开 .env 文件"
        echo "   2. 将 'your_lanhu_cookie_here' 替换为你的实际 Cookie"
        echo "   3. 保存文件"
        echo ""
        read -p "配置完成后按 Enter 继续..."
    else
        echo "❌ 错误：未找到 config.example.env"
        exit 1
    fi
fi

# 检查并加载 .env 文件中的环境变量
echo ""
echo "🔧 正在加载配置..."

# 使用 export 导出环境变量，让子进程（Python）可以访问
set -a  # 自动导出所有变量
source .env
set +a  # 关闭自动导出

if [ -z "$LANHU_COOKIE" ] || [ "$LANHU_COOKIE" = "your_lanhu_cookie_here" ]; then
    echo ""
    echo "❌ 错误：LANHU_COOKIE 未配置"
    echo "请编辑 .env 文件并设置你的蓝湖 Cookie"
    echo ""
    echo "获取 Cookie 的方法："
    echo "1. 登录 https://lanhuapp.com"
    echo "2. 打开浏览器开发者工具（F12）"
    echo "3. 切换到 Network（网络）标签"
    echo "4. 刷新页面"
    echo "5. 点击任意请求"
    echo "6. 从请求头（Request Headers）中复制 'Cookie'"
    exit 1
fi

echo "✅ 配置加载完成"
echo "   Cookie 长度: ${#LANHU_COOKIE} 字符"

# 创建数据目录
mkdir -p data logs

echo ""
echo "🚀 正在启动蓝湖 MCP 服务器..."
echo "=================================="
echo ""
echo "服务器地址：http://localhost:8000/mcp"
echo ""
echo "在 Cursor 中连接，请添加以下配置到 MCP 配置文件："
echo "{
  \"mcpServers\": {
    \"lanhu\": {
      \"url\": \"http://localhost:8000/mcp?role=Developer&name=YourName\"
    }
  }
}"
echo ""
echo "提示：部分 AI 开发工具不支持 URL 中文参数，建议使用英文"
echo ""
echo "按 Ctrl+C 停止服务器"
echo ""

# 运行服务器
python lanhu_mcp_server.py

