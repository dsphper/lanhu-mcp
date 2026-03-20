<div align="center">

# 🎨 Lanhu Skill | 蓝湖数据导出工具

**一键导出蓝湖设计数据到本地项目，结合 AI 进行开发**

**lanhu-skill | 蓝湖导出 | lanhu-export | 蓝湖数据导出**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[快速开始](#-快速开始) • [功能特性](#-核心特性) • [使用文档](#-使用指南)

</div>

---

## 🌟 项目简介

Lanhu Skill 是一个 Claude Code Skill，用于将蓝湖设计数据（页面、设计图、切图）导出到本地项目，便于结合需求文档和技术文档进行 AI 辅助开发。

## ✨ 核心特性

### 📋 页面数据导出
- 获取 Axure 原型的所有页面列表
- 保存每个页面的元数据

### 🎨 设计数据导出
- 批量下载 UI 设计图预览
- 导出设计 Schema JSON（完整设计参数）
- 导出 Sketch JSON（标注信息）

### 🖼️ 切图资源导出
- 自动识别和导出设计切图
- 支持多倍率切图（1x/2x/3x）

### 📝 自动生成文档
- README.md 说明文档
- meta.json 元数据

---

## 📑 目录

- [核心特性](#-核心特性)
- [快速开始](#-快速开始)
- [使用指南](#-使用指南)
- [输出结构](#-输出结构)
- [配置说明](#-配置说明)
- [常见问题](#-常见问题)

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install httpx beautifulsoup4 lxml python-dotenv
```

### 2. 创建配置文件

在项目根目录创建 `.claude/lanhu.config.json`：

```json
{
  "cookie": "你的蓝湖 Cookie",
  "output_base_dir": "docs/lanhu/pages",
  "include_slices": true,
  "include_preview": true,
  "timeout": 30
}
```

### 3. 获取 Cookie

1. 登录蓝湖网页版 (https://lanhuapp.com)
2. 按 F12 打开开发者工具
3. 切换到 Network 标签，刷新页面
4. 找到任意请求，复制 Headers 中的 Cookie 值

### 4. 运行导出

```bash
cd skills/export-lanhu/scripts
python export_lanhu.py "https://lanhuapp.com/web/#/item/project/product?tid=xxx&pid=xxx&docId=xxx"
```

---

## 📖 使用指南

### 命令参数

```bash
python export_lanhu.py <URL> [选项]

选项:
  --output, -o    自定义输出目录
  --no-slices     跳过切图下载
  --no-preview    跳过预览图下载
```

### 示例

```bash
# 基本导出
python export_lanhu.py "https://lanhuapp.com/web/#/item/project/product?tid=xxx&pid=xxx&docId=xxx"

# 指定输出目录
python export_lanhu.py "https://lanhuapp.com/..." --output ./my-designs

# 跳过切图
python export_lanhu.py "https://lanhuapp.com/..." --no-slices
```

---

## 📁 输出结构

```
docs/lanhu/pages/{项目名}-{yyyyMMddHH}/
├── README.md           # 说明文档
├── meta.json           # 元数据
├── pages/              # 页面数据
│   └── {页面名}/
│       └── page.json
├── designs/            # 设计图数据
│   └── {设计名}/
│       ├── schema.json
│       ├── sketch.json
│       └── preview.png
└── slices/             # 切图资源
    └── {切图名}.png
```

### meta.json 格式

```json
{
  "source_url": "https://lanhuapp.com/...",
  "project_name": "项目名称",
  "project_id": "xxx",
  "export_time": "2026-03-20T10:30:00",
  "version_id": "abc123",
  "page_count": 30,
  "design_count": 80,
  "slice_count": 200
}
```

---

## ⚙️ 配置说明

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `cookie` | string | ✅ | - | 蓝湖认证 Cookie |
| `output_base_dir` | string | - | `docs/lanhu/pages` | 输出根目录 |
| `include_slices` | bool | - | `true` | 是否下载切图 |
| `include_preview` | bool | - | `true` | 是否下载预览图 |
| `timeout` | int | - | `30` | HTTP 超时秒数 |

---

## ❓ 常见问题

### Cookie 失效怎么办？

Cookie 有效期通常为几天到几周，失效后需要重新获取并更新配置文件。

### 导出速度慢怎么办？

- 减少下载数据：使用 `--no-slices` 或 `--no-preview`
- 检查网络连接
- 增大 `timeout` 值

### 如何在 AI 开发中使用？

导出的设计数据（JSON + 图片）可以：
1. 作为上下文提供给 AI 助手
2. 结合需求文档进行页面开发
3. 提取精确的设计参数（颜色、字体、间距）

---

## 📄 许可证

[MIT License](LICENSE)

---

## 🙏 致谢

感谢蓝湖（Lanhu）提供的优秀设计协作平台。
