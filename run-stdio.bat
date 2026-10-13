@echo off
cd /d "%~dp0"
REM Optional: LANHU_DISABLE_SYSTEM_PROXY=1 clears inherited proxies and sets NO_PROXY=*
REM so httpx does not fall back to the OS-level proxy settings.
if "%LANHU_DISABLE_SYSTEM_PROXY%"=="1" (
    set "ALL_PROXY="
    set "all_proxy="
    set "HTTP_PROXY="
    set "http_proxy="
    set "HTTPS_PROXY="
    set "https_proxy="
    set "SOCKS_PROXY="
    set "socks_proxy="
    set "NO_PROXY=*"
    set "no_proxy=*"
)
if not exist ".\venv\Scripts\lanhu-mcp.exe" (
    echo Lanhu MCP 尚未安装。请先在项目目录运行 easy-install.bat 1>&2
    exit /b 1
)
.\venv\Scripts\lanhu-mcp.exe --transport stdio
exit /b %errorlevel%
