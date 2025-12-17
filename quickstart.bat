@echo off
REM 蓝湖 MCP 服务器快速启动脚本（Windows）

echo ======================================
echo 🎨 蓝湖 MCP 服务器 - 快速启动
echo ======================================
echo.

REM 检查 Python 版本
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误：未安装 Python
    echo 请从 https://www.python.org/ 安装 Python 3.10 或更高版本
    pause
    exit /b 1
)

echo ✅ Python 已安装
python --version

REM 检查虚拟环境是否存在
if not exist "venv" (
    echo.
    echo 📦 正在创建虚拟环境...
    python -m venv venv
    echo ✅ 虚拟环境创建完成
)

REM 激活虚拟环境
echo.
echo 🔧 正在激活虚拟环境...
call venv\Scripts\activate.bat

REM 安装依赖
echo.
echo 📥 正在安装依赖...
python -m pip install --upgrade pip
pip install -r requirements.txt

REM 安装 Playwright 浏览器
echo.
echo 🌐 正在安装 Playwright 浏览器...
playwright install chromium

REM 检查 .env 是否存在
if not exist ".env" (
    echo.
    echo ⚠️  未找到配置文件 .env
    
    if exist "config.example.env" (
        echo 📝 正在从模板创建 .env...
        copy config.example.env .env
        echo ✅ .env 文件已创建
        echo.
        echo ⚠️  重要提示：请编辑 .env 文件并设置你的 LANHU_COOKIE
        echo    1. 在编辑器中打开 .env 文件
        echo    2. 将 'your_lanhu_cookie_here' 替换为你的实际 Cookie
        echo    3. 保存文件
        echo.
        pause
    ) else (
        echo ❌ 错误：未找到 config.example.env
        pause
        exit /b 1
    )
)

echo.
echo ✅ 配置加载完成

REM 创建数据目录
if not exist "data" mkdir data
if not exist "logs" mkdir logs

echo.
echo 🚀 正在启动蓝湖 MCP 服务器...
echo ======================================
echo.
echo 服务器地址：http://localhost:8000/mcp
echo.
echo 在 Cursor 中连接，请添加以下配置到 MCP 配置文件：
echo {
echo   "mcpServers": {
echo     "lanhu": {
echo       "url": "http://localhost:8000/mcp?role=开发&name=你的名字"
echo     }
echo   }
echo }
echo.
echo 按 Ctrl+C 停止服务器
echo.

REM 运行服务器
python lanhu_mcp_server.py

pause

