# 🚀 Docker 部署指南

## 📋 部署前准备

### 1. 系统要求
- Docker 20.10+
- Docker Compose 2.0+
- 至少 2GB 可用磁盘空间

### 2. 确认配置
`.env` 文件已经配置好了你的蓝湖 Cookie。如需修改配置，请编辑 `.env` 文件。

## 🔧 快速部署

### 方式一：使用 Docker Compose（推荐）

```bash
# 1. 构建并启动服务
docker-compose up -d

# 2. 查看服务状态
docker-compose ps

# 3. 查看实时日志
docker-compose logs -f lanhu-mcp

# 4. 检查服务是否正常运行
curl http://localhost:8000/health
```

### 方式二：使用 Docker 命令

```bash
# 1. 构建镜像
docker build -t lanhu-mcp-server .

# 2. 运行容器
docker run -d \
  --name lanhu-mcp \
  -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  --restart unless-stopped \
  lanhu-mcp-server

# 3. 查看日志
docker logs -f lanhu-mcp

# 4. 检查服务状态
docker ps | grep lanhu-mcp
```

## ✅ 验证部署

### 1. 检查服务健康状态
```bash
curl http://localhost:8000/health
# 预期响应: {"status": "ok"} 或类似的健康检查响应
```

### 2. 访问 MCP 端点
```bash
curl http://localhost:8000/mcp?role=开发&name=测试用户
```

### 3. 查看日志确认
```bash
# Docker Compose
docker-compose logs lanhu-mcp | grep "Server started"

# 或 Docker
docker logs lanhu-mcp | grep "Server started"
```

## 🔌 连接 AI 客户端

### Cursor 配置

在 Cursor 的设置中添加 MCP 服务器配置：

**文件位置:**
- macOS: `~/Library/Application Support/Cursor/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
- Windows: `%APPDATA%\Cursor\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json`
- Linux: `~/.config/Cursor/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`

**配置内容:**
```json
{
  "mcpServers": {
    "lanhu": {
      "url": "http://localhost:8000/mcp?role=后端&name=张三"
    }
  }
}
```

**参数说明:**
- `role`: 你的角色（后端/前端/测试/产品等）
- `name`: 你的姓名（用于团队协作和 @提醒）

### Claude Desktop 配置

编辑配置文件 `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "lanhu": {
      "url": "http://localhost:8000/mcp?role=开发&name=李四"
    }
  }
}
```

## 📊 常用管理命令

### 查看服务状态
```bash
docker-compose ps
# 或
docker ps | grep lanhu-mcp
```

### 查看日志
```bash
# 实时日志
docker-compose logs -f lanhu-mcp

# 最近100行日志
docker-compose logs --tail=100 lanhu-mcp

# 或使用 Docker
docker logs -f lanhu-mcp
docker logs --tail=100 lanhu-mcp
```

### 重启服务
```bash
docker-compose restart lanhu-mcp
# 或
docker restart lanhu-mcp
```

### 停止服务
```bash
docker-compose stop lanhu-mcp
# 或
docker stop lanhu-mcp
```

### 停止并删除容器
```bash
docker-compose down
# 或
docker rm -f lanhu-mcp
```

### 重新构建
```bash
# 重新构建并启动
docker-compose up -d --build

# 或分步操作
docker-compose build
docker-compose up -d
```

### 进入容器调试
```bash
docker-compose exec lanhu-mcp /bin/bash
# 或
docker exec -it lanhu-mcp /bin/bash
```

## 🔍 故障排查

### 1. 容器无法启动

**检查日志:**
```bash
docker-compose logs lanhu-mcp
```

**常见原因:**
- Cookie 格式错误
- 端口被占用（修改 .env 中的 SERVER_PORT）
- 系统资源不足

### 2. Cookie 失效

**症状:** 请求返回 401 或 403 错误

**解决方法:**
1. 重新登录蓝湖网页版
2. 获取新的 Cookie
3. 更新 `.env` 文件
4. 重启服务:
```bash
docker-compose restart lanhu-mcp
```

### 3. 端口冲突

如果 8000 端口被占用，修改配置：

**方式一：修改 .env 文件**
```env
SERVER_PORT=8001
```

**方式二：修改 docker-compose.yml**
```yaml
ports:
  - "8001:8000"  # 宿主机8001端口映射到容器8000端口
```

重启服务后更新 AI 客户端的连接 URL。

### 4. Playwright 浏览器问题

如果截图功能异常：

```bash
# 进入容器
docker-compose exec lanhu-mcp /bin/bash

# 重新安装浏览器
playwright install chromium
playwright install-deps chromium

# 退出并重启
exit
docker-compose restart lanhu-mcp
```

### 5. 数据持久化问题

确认数据目录挂载正确：

```bash
# 检查挂载
docker-compose exec lanhu-mcp ls -la /app/data

# 检查宿主机目录权限
ls -la ./data
ls -la ./logs

# 如果权限有问题
chmod -R 755 ./data ./logs
```

## 📦 数据备份

### 备份数据
```bash
# 备份数据目录
tar -czf lanhu-mcp-backup-$(date +%Y%m%d).tar.gz data/ logs/

# 只备份留言数据
tar -czf lanhu-messages-backup-$(date +%Y%m%d).tar.gz data/messages/
```

### 恢复数据
```bash
# 停止服务
docker-compose stop lanhu-mcp

# 恢复数据
tar -xzf lanhu-mcp-backup-20241217.tar.gz

# 启动服务
docker-compose start lanhu-mcp
```

## 🔒 安全建议

1. **Cookie 安全**
   - 定期更换 Cookie（建议每月一次）
   - 确保 `.env` 文件不被提交到 Git
   - 设置严格的文件权限: `chmod 600 .env`

2. **网络安全**
   - 如果只需本地访问，将 SERVER_HOST 改为 `127.0.0.1`
   - 生产环境建议配置反向代理（Nginx）并启用 HTTPS
   - 使用防火墙限制访问来源

3. **数据安全**
   - 定期备份 `data/messages/` 目录
   - 敏感项目数据不要保留太久
   - 定期清理缓存: `rm -rf data/lanhu_designs/* data/axure_extract_*`

## 🔄 更新服务

### 更新到最新版本

```bash
# 1. 停止服务
docker-compose down

# 2. 拉取最新代码
git pull origin main

# 3. 重新构建并启动
docker-compose up -d --build

# 4. 查看日志确认
docker-compose logs -f lanhu-mcp
```

### 回滚到旧版本

```bash
# 1. 停止服务
docker-compose down

# 2. 切换到指定版本
git checkout v1.0.0  # 替换为实际版本号

# 3. 重新构建并启动
docker-compose up -d --build
```

## 📈 性能优化

### 1. 调整资源限制

在 `docker-compose.yml` 中添加资源限制：

```yaml
services:
  lanhu-mcp:
    # ... 其他配置
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

### 2. 清理缓存

```bash
# 清理旧的截图缓存
docker-compose exec lanhu-mcp find /app/data/lanhu_designs -type f -mtime +30 -delete

# 清理 Axure 资源缓存
docker-compose exec lanhu-mcp find /app/data/axure_extract_* -type f -mtime +30 -delete
```

### 3. 查看资源使用情况

```bash
# 查看容器资源使用
docker stats lanhu-mcp

# 查看磁盘使用
du -sh data/* logs/*
```

## 🌐 生产环境部署建议

### 1. 使用 Nginx 反向代理

**nginx.conf 示例:**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 增加超时时间（用于长时间的截图操作）
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
```

### 2. 启用 HTTPS

使用 Let's Encrypt 免费证书：
```bash
# 安装 certbot
sudo apt-get install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo certbot renew --dry-run
```

### 3. 配置日志轮转

创建 `/etc/logrotate.d/lanhu-mcp`:
```
/path/to/lanhu-mcp/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 root root
}
```

## 💡 使用技巧

### 1. 多环境部署

复制并修改配置文件：
```bash
# 开发环境
cp .env .env.dev
# 生产环境
cp .env .env.prod

# 使用指定配置启动
docker-compose --env-file .env.dev up -d
```

### 2. 查看 MCP 工具列表

```bash
curl http://localhost:8000/mcp?role=开发&name=测试 | jq '.tools[].name'
```

### 3. 监控服务健康

创建简单的健康检查脚本 `health-check.sh`:
```bash
#!/bin/bash
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/mcp)
if [ $STATUS -eq 200 ]; then
    echo "✅ Service is healthy"
    exit 0
else
    echo "❌ Service is down (HTTP $STATUS)"
    exit 1
fi
```

配置 crontab 定时检查：
```bash
# 每5分钟检查一次
*/5 * * * * /path/to/health-check.sh || docker-compose restart lanhu-mcp
```

## 📚 相关文档

- [README.md](README.md) - 项目概述和功能介绍
- [CONTRIBUTING.md](CONTRIBUTING.md) - 贡献指南
- [CHANGELOG.md](CHANGELOG.md) - 更新日志
- [config.example.env](config.example.env) - 配置文件说明

## 🆘 获取帮助

如遇到问题：
1. 查看日志: `docker-compose logs -f lanhu-mcp`
2. 查看本文档的故障排查章节
3. 提交 Issue: https://github.com/dsphper/lanhu-mcp/issues
4. 邮件联系: dsphper@gmail.com

---

祝部署顺利！🎉


<!-- Last checked: 2026-01-18 12:36 -->
