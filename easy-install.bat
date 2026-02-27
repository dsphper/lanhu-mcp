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
REM 步骤 3: 配置蓝湖 Cookie
REM ============================================

echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo 🍪 步骤 3/5: 配置蓝湖 Cookie
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

REM 复制 .env.example 到 .env
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo ✅ 已创建 .env 配置文件
    ) else (
        echo ❌ 未找到 .env.example 文件
        pause
        exit /b 1
    )
) else (
    echo ✅ .env 文件已存在
)

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
echo   8️⃣  用记事本打开当前目录下的 .env 文件
echo      找到 LANHU_COOKIE 这一行
echo      将 your_lanhu_cookie_here 替换为你复制的 Cookie
echo      注意：保留引号，只替换引号内的内容
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

REM 尝试打开浏览器和文件
set /p OPEN_FILES="我可以帮你打开蓝湖网站和 .env 文件吗？(y/n) [y]: "
if "!OPEN_FILES!"=="" set OPEN_FILES=y
if /i "!OPEN_FILES!"=="y" (
    start https://lanhuapp.com
    start notepad .env
    echo ✅ 已打开浏览器和 .env 文件
    echo.
)

echo 完成配置后，按 Enter 继续...
pause >nul

REM 读取 .env 文件中的 Cookie
set LANHU_COOKIE=
for /f "tokens=1,* delims==" %%a in ('type .env ^| findstr /B "LANHU_COOKIE="') do (
    set "LANHU_COOKIE=%%b"
)

REM 移除引号
set LANHU_COOKIE=%LANHU_COOKIE:"=%

REM 验证 Cookie 不为空
if "!LANHU_COOKIE!"=="" (
    echo ❌ Cookie 未配置或配置不正确
    echo 请确保在 .env 文件中正确设置了 LANHU_COOKIE
    pause
    exit /b 1
)

if "!LANHU_COOKIE!"=="your_lanhu_cookie_here" (
    echo ❌ Cookie 未修改，请在 .env 文件中设置正确的 Cookie
    pause
    exit /b 1
)

REM 简单验证 Cookie 格式
echo !LANHU_COOKIE! | findstr /C:"session=" >nul
if errorlevel 1 (
    echo !LANHU_COOKIE! | findstr /C:"user_token=" >nul
    if errorlevel 1 (
        echo ⚠️  Cookie 格式可能不正确
        set /p CONTINUE_ANYWAY="确定要继续吗？(y/n) [n]: "
        if /i not "!CONTINUE_ANYWAY!"=="y" (
            echo 安装已取消
            pause
            exit /b 1
        )
    )
)

echo.
echo ✅ Cookie 配置验证通过！
timeout /t 1 /nobreak >nul

REM ============================================
REM 步骤 4: 创建数据目录
REM ============================================

echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo 📁 步骤 4/5: 创建数据目录
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

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
    echo       "url": "http://localhost:8000/mcp?role=Developer&name=YourName"
    echo     }
    echo   }
    echo }
    echo.
    echo 提示：部分 AI 开发工具不支持 URL 中文参数，建议使用英文
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

