@echo off
setlocal enabledelayedexpansion
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

REM 加载并导出 .env 文件中的环境变量
echo.
echo 🔧 正在加载配置...

REM 读取 .env 文件并设置环境变量
for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
    set "line=%%a"
    REM 跳过注释行和空行
    if not "!line:~0,1!"=="#" if not "!line!"=="" (
        REM 移除引号并设置环境变量
        set "value=%%b"
        set "value=!value:"=!"
        set "%%a=!value!"
    )
)

REM 检查 LANHU_COOKIE 是否已设置
if not defined LANHU_COOKIE (
    echo.
    echo ❌ 错误：LANHU_COOKIE 未配置
    echo 请编辑 .env 文件并设置你的蓝湖 Cookie
    echo.
    echo 获取 Cookie 的方法：
    echo 1. 登录 https://lanhuapp.com
    echo 2. 打开浏览器开发者工具（F12）
    echo 3. 切换到 Network（网络）标签
    echo 4. 刷新页面
    echo 5. 点击任意请求
    echo 6. 从请求头（Request Headers）中复制 'Cookie'
    pause
    exit /b 1
)

if "%LANHU_COOKIE%"=="your_lanhu_cookie_here" (
    echo.
    echo ❌ 错误：LANHU_COOKIE 未配置
    echo 请编辑 .env 文件并设置你的蓝湖 Cookie
    pause
    exit /b 1
)

echo ✅ 配置加载完成
call :strlen LANHU_COOKIE cookie_len
echo    Cookie 长度: %cookie_len% 字符

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
echo       "url": "http://localhost:8000/mcp?role=Developer&name=YourName"
echo     }
echo   }
echo }
echo.
echo 提示：部分 AI 开发工具不支持 URL 中使用中文参数值，建议使用英文
echo 按 Ctrl+C 停止服务器
echo.

REM 运行服务器
python lanhu_mcp_server.py

pause

REM 计算字符串长度的函数
:strlen
setlocal enabledelayedexpansion
set "str=!%~1!"
set "len=0"
:strlen_loop
if defined str (
    set "str=!str:~1!"
    set /a len+=1
    goto :strlen_loop
)
endlocal & set "%~2=%len%"
goto :eof
