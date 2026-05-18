#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"
export MCP_TRANSPORT=stdio
exec ./venv/bin/python lanhu_mcp_server.py
