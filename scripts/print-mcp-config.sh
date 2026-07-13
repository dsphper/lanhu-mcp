#!/bin/bash
# 根据 .env 中的 SERVER_PORT 输出 MCP 连接地址与 Cursor 配置示例

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -f "$ROOT_DIR/.env" ]; then
    set -a
    # shellcheck source=/dev/null
    source "$ROOT_DIR/.env"
    set +a
fi

SERVER_PORT="${SERVER_PORT:-8000}"
MCP_URL="http://localhost:${SERVER_PORT}/mcp"

echo "服务器地址：${MCP_URL}"
echo ""
echo "在 Cursor 中连接，请添加以下配置到 MCP 配置文件："
echo "{"
echo "  \"mcpServers\": {"
echo "    \"lanhu\": {"
echo "      \"url\": \"${MCP_URL}?role=Developer&name=YourName\""
echo "    }"
echo "  }"
echo "}"
echo ""
echo "提示：部分 AI 开发工具不支持 URL 中文参数，建议使用英文"
