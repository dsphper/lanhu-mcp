@echo off
cd /d "%~dp0"
set MCP_TRANSPORT=stdio
.\venv\Scripts\python.exe lanhu_mcp_server.py
