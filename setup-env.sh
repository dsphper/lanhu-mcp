#!/bin/bash

# 蓝湖 MCP Docker 快速部署脚本
# 使用方法: ./setup-env.sh

set -e

echo "🚀 蓝湖 MCP Server - Docker 部署助手"
echo "======================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检测 docker compose 命令（兼容 compose v1/compose v2）
detect_docker_compose() {
    if command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
        echo -e "${YELLOW}ℹ️  检测到 docker-compose (Compose V1)，将使用该命令${NC}"
    elif docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
        echo -e "${YELLOW}ℹ️  检测到 docker compose (Compose V2)，将使用该命令${NC}"
    else
        return 1
    fi
    return 0
}

# 检查 Docker 环境
echo "📦 检查 Docker 环境..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ 未安装 Docker，请先安装 Docker${NC}"
    echo "   官方文档: https://docs.docker.com/get-docker/"
    exit 1
fi

# 检查 Compose 命令
if ! detect_docker_compose; then
    echo -e "${RED}❌ 未安装 Docker Compose（V1/V2），请先安装${NC}"
    echo "   Compose V2 安装文档: https://docs.docker.com/compose/install/linux/"
    echo "   Compose V1 安装文档: https://docs.docker.com/compose/install/other/"
    exit 1
fi

echo -e "${GREEN}✅ Docker 环境检查通过${NC}"
echo ""

# 创建 .env 文件
echo "📝 创建配置文件..."

# 你的蓝湖 Cookie (已从用户输入中获取)
LANHU_COOKIE='your_lanhu_cookie_here'

cat > .env << EOF
# 蓝湖 MCP 服务器配置
# ⚠️ 注意：此文件包含敏感信息，不要提交到 git！

# ==============================================
# 必需配置
# ==============================================

# 蓝湖 Cookie（必需）
LANHU_COOKIE="$LANHU_COOKIE"

# ==============================================
# 服务器配置（可选）
# ==============================================

# 服务器主机地址
SERVER_HOST="0.0.0.0"

# 服务器端口
SERVER_PORT=8000

# ==============================================
# 飞书机器人配置（可选）
# ==============================================

# 飞书 Webhook URL（可选 - 如不需要飞书通知请留空）
FEISHU_WEBHOOK_URL=""

# ==============================================
# 数据存储配置（可选）
# ==============================================

# 数据存储目录
DATA_DIR="./data"

# ==============================================
# 性能配置（可选）
# ==============================================

# HTTP 请求超时时间（秒）
HTTP_TIMEOUT=30

# 浏览器视口宽度
VIEWPORT_WIDTH=1920

# 浏览器视口高度
VIEWPORT_HEIGHT=1080

# ==============================================
# 开发配置（可选）
# ==============================================

# 调试模式
DEBUG="false"
EOF

echo -e "${GREEN}✅ 配置文件创建成功: .env${NC}"
chmod 600 .env
echo -e "${GREEN}✅ 已设置安全权限 (600)${NC}"
echo ""

# 创建数据目录
echo "📁 创建数据目录..."
mkdir -p data logs
echo -e "${GREEN}✅ 目录创建成功${NC}"
echo ""

# 构建和启动
echo "🏗️  构建 Docker 镜像..."
echo -e "${YELLOW}⏳ 这可能需要几分钟时间，请耐心等待...${NC}"
$COMPOSE_CMD build

echo ""
echo "🚀 启动服务..."
$COMPOSE_CMD up -d

echo ""
echo "⏱️  等待服务启动（10秒）..."
sleep 10

# 检查服务状态
echo ""
echo "🔍 检查服务状态..."
# 兼容两种 compose 命令的 ps 输出格式
if $COMPOSE_CMD ps | grep -q "Up"; then
    if [ -f ".env" ]; then
        set -a
        # shellcheck source=/dev/null
        source .env
        set +a
    fi
    SERVER_PORT="${SERVER_PORT:-8000}"

    echo -e "${GREEN}✅ 服务启动成功！${NC}"
    echo ""
    echo "📊 服务信息:"
    $COMPOSE_CMD ps
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}🎉 部署完成！${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "📝 服务访问地址:"
    echo "   http://localhost:${SERVER_PORT}/mcp?role=开发&name=你的名字"
    echo ""
    echo "🔧 常用命令:"
    echo "   查看日志: $COMPOSE_CMD logs -f lanhu-mcp"
    echo "   停止服务: $COMPOSE_CMD stop"
    echo "   重启服务: $COMPOSE_CMD restart"
    echo "   删除服务: $COMPOSE_CMD down"
    echo ""
    echo "📚 配置 AI 客户端:"
    echo "   请参考 DEPLOY.md 文档中的「连接 AI 客户端」章节"
    echo ""
    echo "💡 提示:"
    echo "   - 配置文件位置: $(pwd)/.env"
    echo "   - 数据存储位置: $(pwd)/data"
    echo "   - 日志存储位置: $(pwd)/logs"
    echo ""
else
    echo -e "${RED}❌ 服务启动失败${NC}"
    echo ""
    echo "📋 查看错误日志:"
    $COMPOSE_CMD logs --tail=50 lanhu-mcp
    echo ""
    echo "💡 常见问题排查:"
    echo "   1. Cookie 是否正确？"
    echo "   2. 端口 ${SERVER_PORT:-8000} 是否被占用？"
    echo "   3. Docker 资源是否充足？"
    echo ""
    echo "📚 详细文档: 请查看 DEPLOY.md"
    exit 1
fi