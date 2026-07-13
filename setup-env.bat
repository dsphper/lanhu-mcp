@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
REM 蓝湖 MCP Docker 快速部署脚本 (Windows)
REM 适配 Docker Desktop v20.10+ (docker compose 无横线)
REM 使用方法: setup-env.bat

echo.
echo ========================================
echo 🚀 蓝湖 MCP Server - Docker 部署助手
echo ========================================
echo.

REM 检查 Docker 基础环境
echo 📦 检查 Docker 环境...
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未安装 Docker，请先安装 Docker Desktop
    echo    官方文档: https://docs.docker.com/desktop/windows/install/
    pause
    exit /b 1
)

REM 兼容检测 docker-compose / docker compose
echo 📦 检测 Docker Compose 命令格式...
set "COMPOSE_CMD="
docker compose version >nul 2>&1
if not errorlevel 1 (
    set "COMPOSE_CMD=docker compose"
    echo ✅ 检测到 Docker Compose (无横线) 格式: docker compose
) else (
    docker-compose --version >nul 2>&1
    if not errorlevel 1 (
        set "COMPOSE_CMD=docker-compose"
        echo ✅ 检测到 Docker Compose (有横线) 格式: docker-compose
    ) else (
        echo ❌ 未安装 Docker Compose，请先安装
        echo    官方文档: https://docs.docker.com/compose/install/
        pause
        exit /b 1
    )
)

echo ✅ Docker 环境检查通过
echo.

REM 创建 .env 文件
echo 📝 创建配置文件...

(
echo # 蓝湖 MCP 服务器配置
echo # ⚠️ 注意：此文件包含敏感信息，不要提交到 git！
echo.
echo # ==============================================
echo # 必需配置
echo # ==============================================
echo.
echo # 蓝湖 Cookie（必需）
echo LANHU_COOKIE="your_lanhu_cookie_here"
echo.
echo # ==============================================
echo # 服务器配置（可选）
echo # ==============================================
echo.
echo # 服务器主机地址
echo SERVER_HOST="0.0.0.0"
echo.
echo # 服务器端口
echo SERVER_PORT=8000
echo.
echo # ==============================================
echo # 飞书机器人配置（可选）
echo # ==============================================
echo.
echo # 飞书 Webhook URL（可选 - 如不需要飞书通知请留空）
echo FEISHU_WEBHOOK_URL=""
echo.
echo # ==============================================
echo # 数据存储配置（可选）
echo # ==============================================
echo.
echo # 数据存储目录
echo DATA_DIR="./data"
echo.
echo # ==============================================
echo # 性能配置（可选）
echo # ==============================================
echo.
echo # HTTP 请求超时时间（秒）
echo HTTP_TIMEOUT=30
echo.
echo # 浏览器视口宽度
echo VIEWPORT_WIDTH=1920
echo.
echo # 浏览器视口高度
echo VIEWPORT_HEIGHT=1080
echo.
echo # ==============================================
echo # 开发配置（可选）
echo # ==============================================
echo.
echo # 调试模式
echo DEBUG="false"
) > .env

echo ✅ 配置文件创建成功: .env
echo.

REM 创建数据目录
echo 📁 创建数据目录...
if not exist "data" mkdir data
if not exist "logs" mkdir logs
echo ✅ 目录创建成功
echo.

REM 构建和启动
echo 🏗️  构建 Docker 镜像...
echo ⏳ 这可能需要几分钟时间，请耐心等待...
%COMPOSE_CMD% build

echo.
echo 🚀 启动服务...
%COMPOSE_CMD% up -d

echo.
echo ⏱️  等待服务启动（10秒）...
timeout /t 10 /nobreak >nul

REM 检查服务状态
echo.
echo 🔍 检查服务状态...
%COMPOSE_CMD% ps | findstr "Up" >nul
if not errorlevel 1 (
    echo ✅ 服务启动成功！
    echo.
    echo 📊 服务信息:
    %COMPOSE_CMD% ps
    echo.
    echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    echo 🎉 部署完成！
    echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    echo.
    if not defined SERVER_PORT set SERVER_PORT=8000
    for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
        if /i "%%a"=="SERVER_PORT" (
            set "value=%%b"
            set "value=!value:"=!"
            if not "!value!"=="" set "SERVER_PORT=!value!"
        )
    )
    echo 📝 服务访问地址:
    echo    http://localhost:!SERVER_PORT!/mcp?role=开发^&name=你的名字
    echo.
    echo 🔧 常用命令:
    echo    查看日志: %COMPOSE_CMD% logs -f lanhu-mcp
    echo    停止服务: %COMPOSE_CMD% stop
    echo    重启服务: %COMPOSE_CMD% restart
    echo    删除服务: %COMPOSE_CMD% down
    echo.
    echo 📚 配置 AI 客户端:
    echo    请参考 DEPLOY.md 文档中的「连接 AI 客户端」章节
    echo.
    echo 💡 提示:
    echo    - 配置文件位置: %CD%\.env
    echo    - 数据存储位置: %CD%\data
    echo    - 日志存储位置: %CD%\logs
    echo.
) else (
    echo ❌ 服务启动失败
    echo.
    echo 📋 查看错误日志:
    %COMPOSE_CMD% logs --tail=50 lanhu-mcp
    echo.
    echo 💡 常见问题排查:
    echo    1. Cookie 是否正确？
    echo    2. 端口 !SERVER_PORT! 是否被占用？
    echo    3. Docker Desktop 是否正在运行？
    echo    4. Docker 资源是否充足？
    echo    5. 确认 Docker Compose 命令格式是否正确（docker compose / docker-compose）
    echo.
    echo 📚 详细文档: 请查看 DEPLOY.md
    pause
    exit /b 1
)

pause