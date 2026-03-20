# Export Lanhu Skill 设计规格

## 概述

将蓝湖设计数据获取方式从 MCP Server 改为 Claude Code Skill，实现一键导出设计数据到本地项目。

## 需求背景

- **目标**：将蓝湖设计数据（JSON + 切图）保存到调用项目的 `docs/lanhu/pages/` 目录
- **用途**：结合需求文档、技术文档进行页面开发
- **约束**：在新分支开发，删除现有 MCP 工具

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│  Claude Code Session                                         │
│                                                              │
│  /export-lanhu <URL>                                        │
│       │                                                      │
│       ▼                                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Skill: skills/export-lanhu/SKILL.md                │   │
│  │  • 解析参数，读取配置                                  │   │
│  │  • 调用 Bash 执行 Python 导出脚本                      │   │
│  └─────────────────────────────────────────────────────┘   │
│       │                                                      │
│       ▼                                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Python: skills/export-lanhu/scripts/export_lanhu.py│   │
│  │                                                       │   │
│  │  数据获取流程（层级获取）：                            │   │
│  │  1. URL → 获取 Pages 列表                             │   │
│  │  2. 每个 Page → 获取 Page 详情                        │   │
│  │  3. 每个 Page → 获取 Design 信息                      │   │
│  │                                                       │   │
│  │  • 下载图片和切图                                      │   │
│  │  • 保存 JSON + 图片到目标目录                          │   │
│  │  • 生成 README.md                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│       │                                                      │
│       ▼                                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  输出: docs/lanhu/pages/{项目名}-{yyyyMMddHH}/       │   │
│  │  ├── pages/             # 页面数据                    │   │
│  │  ├── designs/           # 设计数据                    │   │
│  │  ├── slices/            # 切图资源                    │   │
│  │  ├── README.md          # 说明文档                    │   │
│  │  └── meta.json          # 元数据                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 文件结构

### 新增文件

```
lanhu-mcp/
├── skills/export-lanhu/                  # Skill 目录
│   ├── SKILL.md                          # Skill 定义（触发条件+指令）
│   │
│   ├── scripts/                          # Python 脚本
│   │   ├── export_lanhu.py               # 主导出脚本
│   │   └── lanhu_api.py                  # 蓝湖 API 封装
│   │
│   ├── references/                       # 参考文档
│   │   ├── api-reference.md              # API 接口文档
│   │   └── output-format.md              # 输出格式说明
│   │
│   └── assets/                           # 资源文件
│       ├── lanhu.config.example.json     # 配置文件模板
│       └── README.template.md            # 说明文档模板
```

### 删除文件

```
lanhu-mcp/
├── lanhu_mcp_server.py        # 删除：整个 MCP Server 文件
├── Dockerfile                 # 删除：Docker 配置
├── docker-compose.yml         # 删除：Docker Compose 配置
└── .env.example               # 删除：改用 lanhu.config.json
```

### 修改文件

```
lanhu-mcp/
├── requirements.txt           # 更新：移除 fastmcp 依赖
├── README.md                  # 更新：更新使用说明
└── tests/                     # 更新：测试文件
```

## 输出目录结构

```
docs/lanhu/pages/{项目名}-{yyyyMMddHH}/
├── README.md                     # 说明文档（自动生成）
├── meta.json                     # 元数据（来源、时间、版本等）
│
├── pages/                        # 页面数据
│   ├── {页面名1}/
│   │   ├── page.json             # 页面元数据
│   │   └── content.json          # 页面内容
│   └── {页面名2}/
│       ├── page.json
│       └── content.json
│
├── designs/                      # 设计图数据
│   ├── {设计名1}/
│   │   ├── schema.json           # 设计 Schema JSON
│   │   ├── sketch.json           # Sketch JSON
│   │   └── preview.png           # 设计预览图
│   └── {设计名2}/
│       ├── schema.json
│       ├── sketch.json
│       └── preview.png
│
└── slices/                       # 切图资源
    ├── icon-arrow.png
    ├── bg-header.png
    └── ...
```

### README.md 内容

- **项目名称**：蓝湖项目名称
- **数据来源**：蓝湖项目链接
- **导出时间**：ISO 8601 格式
- **页面列表**：页面名称、链接、子页面数
- **设计图列表**：名称、尺寸
- **切图清单**：文件名、尺寸、用途建议
- **使用说明**：如何引用数据进行开发

### meta.json 格式

```json
{
  "source_url": "https://lanhuapp.com/...",
  "project_name": "首页设计",
  "project_id": "xxx",
  "export_time": "2026-03-20T10:30:00",
  "version_id": "abc123",
  "page_count": 8,
  "design_count": 5,
  "slice_count": 23
}
```

## 配置文件

### 位置

调用项目的 `.claude/lanhu.config.json`

### 格式

```json
{
  "cookie": "你的蓝湖 Cookie（必填）",
  "output_base_dir": "docs/lanhu/pages",
  "include_slices": true,
  "include_preview": true,
  "download_concurrent": 5,
  "timeout": 30
}
```

### 字段说明

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `cookie` | string | ✅ | - | 蓝湖认证 Cookie |
| `output_base_dir` | string | - | `docs/lanhu/pages` | 输出根目录 |
| `include_slices` | bool | - | `true` | 是否下载切图 |
| `include_preview` | bool | - | `true` | 是否下载设计预览图 |
| `download_concurrent` | int | - | `5` | 并发下载数 |
| `timeout` | int | - | `30` | HTTP 超时秒数 |

## SKILL.md 定义

```markdown
---
name: export-lanhu
description: |
  导出蓝湖设计数据到本地项目。

  触发场景：导出蓝湖、蓝湖设计、下载切图、同步设计稿、拉取设计数据、
  UI设计导出、设计数据保存、蓝湖数据导出、设计稿同步。

  当用户提到蓝湖、设计稿、切图、UI设计导出时，使用此 Skill。
compatibility:
  tools: [Bash, Read, Write]
  dependencies: [httpx]
---

## 使用方式

/export-lanhu <URL> [--output <目录>] [--no-slices] [--no-preview]

## 参数

| 参数 | 说明 |
|------|------|
| `URL` | 蓝湖项目链接（必填） |
| `--output` | 自定义输出目录 |
| `--no-slices` | 跳过切图下载 |
| `--no-preview` | 跳过预览图下载 |

## 执行步骤

1. **读取配置**：从 `.claude/lanhu.config.json` 读取 Cookie 和配置
2. **解析 URL**：提取 project_id、team_id 等参数
3. **获取 Pages 列表**：调用蓝湖 API 获取页面列表
4. **获取 Page 详情**：遍历每个页面获取详细信息
5. **获取 Design 信息**：获取每个页面关联的设计数据
6. **下载设计数据**：Schema JSON + Sketch JSON + 预览图
7. **下载切图**：获取所有切图资源
8. **生成说明文档**：README.md + meta.json

## 输出

数据保存到 `docs/lanhu/pages/{项目名}-{yyyyMMddHH}/`
```

## 代码复用策略

从 `lanhu_mcp_server.py` 提取以下代码到 `lanhu_api.py`：

### 保留的代码

- `LanhuExtractor` 类的核心 API 方法
  - `parse_url()` - URL 解析
  - `get_pages_list()` - 获取页面列表
  - `get_page_info()` - 获取页面详情
  - `get_design_schema_json()` - 获取设计 Schema
  - `get_sketch_json()` - 获取 Sketch JSON
  - `get_design_slices_info()` - 获取切图信息
- HTTP 客户端配置
- 常量定义（BASE_URL 等）

### 删除的代码

- `@mcp.tool()` 装饰器和所有 MCP 工具定义
- HTML/CSS 转换逻辑（`convert_lanhu_to_html` 等）
- 截图相关代码（`screenshot_page_internal`）
- Playwright 相关代码
- 消息存储（`MessageStore`）
- 飞书通知相关代码

## 依赖变更

### requirements.txt 更新

```txt
# 移除
fastmcp>=2.0.0
playwright>=1.48.0
htmlmin2>=0.1.12

# 保留
httpx>=0.27.0
beautifulsoup4>=4.12.0
lxml>=5.0.0
python-dotenv>=1.0.0
```

## 实现步骤

1. 创建新分支 `feature/export-lanhu-skill`
2. 创建 Skill 目录结构 `skills/export-lanhu/`
3. 提取 API 代码到 `scripts/lanhu_api.py`
4. 实现 `scripts/export_lanhu.py` 主脚本
5. 创建 SKILL.md 和参考文档
6. 删除 MCP Server 相关文件
7. 更新 requirements.txt
8. 更新 README.md
9. 更新测试文件
10. 测试验证

## 验收标准

1. 执行 `/export-lanhu <URL>` 能成功导出数据
2. 输出目录结构符合设计
3. README.md 包含项目名称和完整信息
4. 配置从 `.claude/lanhu.config.json` 正确读取
5. 原有 MCP Server 代码已删除
6. 测试通过
