@echo off
REM 根据 .env 中的 SERVER_PORT 输出 MCP 连接地址与 Cursor 配置示例
setlocal enabledelayedexpansion

set "SERVER_PORT=8000"
if exist ".env" (
    for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
        set "line=%%a"
        if /i "%%a"=="SERVER_PORT" (
            set "value=%%b"
            set "value=!value:"=!"
            if not "!value!"=="" set "SERVER_PORT=!value!"
        )
    )
)

set "MCP_URL=http://localhost:!SERVER_PORT!/mcp"

echo 服务器地址：!MCP_URL!
echo.
echo 在 Cursor 中连接，请添加以下配置到 MCP 配置文件：
echo {
echo   "mcpServers": {
echo     "lanhu": {
echo       "url": "!MCP_URL!?role=Developer&name=YourName"
echo     }
echo   }
echo }
echo.
echo 提示：部分 AI 开发工具不支持 URL 中文参数，建议使用英文

endlocal
