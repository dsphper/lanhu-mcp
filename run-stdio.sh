#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

# Optional: LANHU_DISABLE_SYSTEM_PROXY=1 clears inherited proxies (Cursor SOCKS, etc.)
# and sets NO_PROXY=* so httpx does not fall back to the OS-level proxy settings.
if [ "${LANHU_DISABLE_SYSTEM_PROXY:-0}" = "1" ]; then
    unset ALL_PROXY all_proxy HTTP_PROXY http_proxy HTTPS_PROXY https_proxy SOCKS_PROXY socks_proxy || true
    export NO_PROXY="*" no_proxy="*"
fi

if [ -x "./venv/bin/lanhu-mcp" ]; then
    exec ./venv/bin/lanhu-mcp --transport stdio
fi

echo "Lanhu MCP 尚未安装。请先在项目目录运行：bash easy-install.sh" >&2
exit 1
