@echo off
chcp 65001 >nul
REM 蓝湖 MCP Server - 超级简单安装脚本 (Windows)
REM 专为小白用户设计，交互式引导安装

setlocal enabledelayedexpansion

cls

echo.
echo ╔═══════════════════════════════════════════════════╗
echo ║                                                   ║
echo ║     🎨 蓝湖 MCP Server - 一键安装程序            ║
echo ║                                                   ║
echo ║     让 AI 助手共享团队知识，打破 AI IDE 孤岛     ║
echo ║                                                   ║
echo ╚═══════════════════════════════════════════════════╝
echo.
echo 欢迎！这个脚本会帮你自动完成所有安装步骤
echo 预计耗时：3-5 分钟
echo.
echo 按 Enter 开始安装，或按 Ctrl+C 取消
pause >nul

REM ============================================
REM 步骤 1: 环境检查
REM ============================================

echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo 📦 步骤 1/5: 检查系统环境
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

REM 检查 Python
echo 正在检查 Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未检测到 Python
    echo.
    echo 请先安装 Python 3.10 或更高版本：
    echo   官网: https://www.python.org/downloads/
    echo.
    echo 安装时请务必勾选 "Add Python to PATH"
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo ✅ Python %PYTHON_VERSION%

REM 检查 pip
pip --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未检测到 pip
    pause
    exit /b 1
)
echo ✅ pip 已安装

echo.
echo 🎉 环境检查通过！
timeout /t 1 /nobreak >nul

REM ============================================
REM 步骤 2: 安装依赖
REM ============================================

echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo 📥 步骤 2/5: 安装依赖包
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

REM 创建虚拟环境
if not exist "venv" (
    echo 正在创建 Python 虚拟环境...
    python -m venv venv
    echo ✅ 虚拟环境创建完成
) else (
    echo ✅ 虚拟环境已存在
)

REM 激活虚拟环境
echo 正在激活虚拟环境...
call venv\Scripts\activate.bat

REM 升级 pip
echo 正在升级 pip...
python -m pip install --upgrade pip -q

REM 安装依赖
echo 正在安装项目依赖...
echo （这可能需要 1-2 分钟，请耐心等待）
pip install -r requirements.txt -q

echo ✅ 依赖安装完成

REM 安装 Playwright 浏览器
echo.
echo 正在安装 Playwright 浏览器...
echo （首次安装需要下载 Chromium，可能需要 1-2 分钟）
playwright install chromium

echo.
echo 🎉 依赖安装完成！
timeout /t 1 /nobreak >nul

REM ============================================
REM 步骤 3: 获取蓝湖 Cookie（交互式）
REM ============================================

echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo 🍪 步骤 3/5: 获取蓝湖 Cookie
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo 这是唯一需要你手动操作的步骤，很简单！
echo.
echo 请按照以下步骤操作：
echo.
echo   1️⃣  在浏览器打开：https://lanhuapp.com 并登录
echo.
echo   2️⃣  按下键盘 F12 键
echo      会打开开发者工具
echo.
echo   3️⃣  点击顶部的 "Network"（网络）标签
echo.
echo   4️⃣  按 F5 刷新页面
echo.
echo   5️⃣  在左侧请求列表中点击 第一个请求
echo.
echo   6️⃣  右侧找到 "Request Headers" 部分
echo      找到 "Cookie:" 开头的那一行
echo.
echo   7️⃣  选中并复制 整个 Cookie 值
echo      （Cookie 很长，确保全部复制）
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

REM 尝试打开浏览器
set /p OPEN_BROWSER="我可以帮你打开蓝湖网站吗？(y/n) [y]: "
if "!OPEN_BROWSER!"=="" set OPEN_BROWSER=y
if /i "!OPEN_BROWSER!"=="y" (
    start https://lanhuapp.com
    echo ✅ 已打开浏览器
    echo.
)

echo 复制好 Cookie 后，粘贴到下面：
echo.
set /p LANHU_COOKIE="> "

REM 验证 Cookie 不为空
if "!LANHU_COOKIE!"=="" (
    echo ❌ Cookie 不能为空
    pause
    exit /b 1
)

echo.
echo ✅ Cookie 已接收！
timeout /t 1 /nobreak >nul

REM ============================================
REM 步骤 4: 生成配置文件
REM ============================================

echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo ⚙️  步骤 4/5: 生成配置文件
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

REM 创建 .env 文件
(
echo # 蓝湖 MCP 服务器配置
echo # 由 easy-install.bat 自动生成
echo.
echo # ==============================================
echo # 必需配置
echo # ==============================================
echo.
echo # 蓝湖 Cookie（必需^)
echo LANHU_COOKIE="!LANHU_COOKIE!"
echo.
echo # ==============================================
echo # 服务器配置
echo # ==============================================
echo.
echo SERVER_HOST="0.0.0.0"
echo SERVER_PORT=8000
echo.
echo # ==============================================
echo # 数据存储
echo # ==============================================
echo.
echo DATA_DIR="./data"
echo.
echo # ==============================================
echo # 性能配置
echo # ==============================================
echo.
echo HTTP_TIMEOUT=30
echo VIEWPORT_WIDTH=1920
echo VIEWPORT_HEIGHT=1080
echo.
echo # ==============================================
echo # 调试选项
echo # ==============================================
echo.
echo DEBUG="false"
) > .env

echo ✅ 配置文件已生成

REM 创建数据目录
if not exist "data" mkdir data
if not exist "logs" mkdir logs
echo ✅ 数据目录已创建

timeout /t 1 /nobreak >nul

REM ============================================
REM 步骤 5: 启动服务
REM ============================================

echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo 🚀 步骤 5/5: 启动服务
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

set /p START_NOW="是否现在启动服务？(y/n) [y]: "
if "!START_NOW!"=="" set START_NOW=y

if /i "!START_NOW!"=="y" (
    echo.
    echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    echo 🎉 安装成功！服务正在启动...
    echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    echo.
    echo 服务器地址：http://localhost:8000/mcp
    echo.
    echo 下一步：在 Cursor 中配置 MCP
    echo.
    echo 请将以下配置添加到 Cursor 的 MCP 配置文件中：
    echo.
    echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    echo {
    echo   "mcpServers": {
    echo     "lanhu": {
    echo       "url": "http://localhost:8000/mcp?role=开发&name=你的名字"
    echo     }
    echo   }
    echo }
    echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    echo.
    echo 配置方法：
    echo   1. 打开 Cursor
    echo   2. 按 Ctrl+Shift+P
    echo   3. 输入 'MCP' 找到 MCP 配置
    echo   4. 粘贴上面的配置
    echo.
    echo 按 Ctrl+C 可以停止服务器
    echo.
    echo 正在启动服务器...
    echo.
    
    REM 运行服务器
    python lanhu_mcp_server.py
) else (
    echo.
    echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    echo 🎉 安装成功！
    echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    echo.
    echo 稍后运行服务器，请执行：
    echo   venv\Scripts\activate.bat
    echo   python lanhu_mcp_server.py
    echo.
    pause
)

