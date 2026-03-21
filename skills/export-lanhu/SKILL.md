---
name: export-lanhu
description: |
  导出蓝湖设计数据到本地项目（支持关键词过滤）。

  触发场景：导出蓝湖、蓝湖设计、下载切图、同步设计稿、拉取设计数据、
  UI设计导出、设计数据保存、蓝湖数据导出、设计稿同步、按关键词导出设计。

  当用户提到蓝湖、设计稿、切图、UI设计导出时，使用此 Skill。
compatibility:
  tools: [Bash, Read, Write]
  dependencies: [httpx]
---

## 使用方式

用户可以通过自然语言描述导出需求：

- "导出蓝湖 <URL> 和登录相关的页面数据"
- "导出蓝湖 <URL> 的全部设计"
- "导出蓝湖 <URL> 中登录、注册相关的设计"

## 前置条件

1. 在项目根目录创建 `.claude/lanhu.config.json` 配置文件
2. 配置文件中必须包含 `cookie` 字段

## 配置文件示例

```json
{
  "cookie": "你的蓝湖 Cookie",
  "output_base_dir": "docs/lanhu/pages",
  "include_slices": true,
  "include_preview": true,
  "timeout": 300
}
```

## 获取 Cookie 方法

1. 登录蓝湖网页版 (https://lanhuapp.com)
2. 按 F12 打开开发者工具
3. 切换到 Network 标签
4. 刷新页面，找到任意请求
5. 在 Headers 中找到 Cookie 字段
6. 复制完整的 Cookie 值

## 执行流程

### 步骤 1：解析用户输入

1. **提取蓝湖 URL**
   - 匹配 `lanhuapp.com` 开头的链接
   - 支持 `http://` 和 `https://`

2. **提取关键词**
   - 从用户描述中识别业务词（如"登录"、"注册"、"支付"）
   - 常见关键词模式：
     - "和 X 相关的"
     - "X 相关的页面"
     - "包含 X 的设计"
     - "X 相关"
   - 如果用户说"全部"、"所有"或未指定关键词，则无关键词

3. **多关键词处理**
   - 多个关键词用逗号连接传递给脚本

### 步骤 2：获取设计列表（预览）

执行命令获取设计列表：

```bash
cd skills/export-lanhu/scripts
python export_lanhu.py "<URL>" --keyword <关键词> --list
```

无关键词时：

```bash
python export_lanhu.py "<URL>" --list
```

**输出 JSON 格式：**

```json
{
  "source_url": "https://lanhuapp.com/...",
  "project_name": "电商APP设计",
  "project_id": "xxx",
  "total": 28,
  "matched_count": 5,
  "matched": [
    {"id": "abc", "name": "登录页"},
    {"id": "def", "name": "登录页-手机号"}
  ],
  "unmatched_count": 23,
  "unmatched": [
    {"id": "xxx", "name": "商品详情"}
  ]
}
```

### 步骤 3：展示结果并确认

解析 JSON 输出，展示给用户：

```
🎯 匹配"登录"的设计图 (5/28)：

  ✅ 登录页
  ✅ 登录页-手机号
  ✅ 登录页-验证码
  ✅ 登录成功
  ✅ 忘记登录密码

📋 其他设计（23 个）：商品详情、支付成功、我的...

是否导出这 5 个设计？
```

**交互选项：**
- 用户确认 → 执行导出
- 用户要求调整 → 重新过滤或使用 `--ids` 精确指定
- 用户说"全部导出" → 不带关键词导出所有设计

### 步骤 4：执行导出

用户确认后执行：

```bash
python export_lanhu.py "<URL>" --keyword <关键词>
```

精确指定 ID：

```bash
python export_lanhu.py "<URL>" --ids <id1>,<id2>,<id3>
```

导出全部（无过滤）：

```bash
python export_lanhu.py "<URL>"
```

## 输出

数据保存到 `docs/lanhu/pages/{项目名}-{yyyyMMddHH}/`

```
{项目名}-{yyyyMMddHH}/
├── designs/         # 设计图数据
│   └── {设计名}/
│       ├── schema.json
│       ├── sketch.json
│       └── preview.png
├── slices/          # 切图资源
│   └── {切图名}.png
├── meta.json        # 元数据
└── README.md        # 说明文档
```

## 关键词匹配规则

- 匹配方式：包含匹配（设计名包含关键词即匹配）
- 多关键词：OR 逻辑（匹配任意一个即可）
- 大小写：不区分

## 可选参数

| 参数 | 说明 |
|------|------|
| `--output, -o` | 自定义输出目录 |
| `--no-slices` | 跳过切图下载 |
| `--no-preview` | 跳过预览图下载 |

## 示例场景

**场景 1：导出登录相关设计**
```
用户：导出蓝湖 https://lanhuapp.com/... 和登录相关的页面数据
Claude：执行预览 → 展示匹配结果 → 用户确认 → 执行导出
```

**场景 2：导出全部设计**
```
用户：导出蓝湖 https://lanhuapp.com/... 的所有设计
Claude：直接执行导出（无过滤）
```

**场景 3：精确指定设计**
```
用户：导出蓝湖 https://lanhuapp.com/... 只要登录页和注册页
Claude：预览 → 用户确认后用 --ids 精确导出
```
