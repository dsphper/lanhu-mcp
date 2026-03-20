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

```bash
/export-lanhu <URL> [--output <目录>] [--no-slices] [--no-preview]
```

## 参数

| 参数 | 说明 |
|------|------|
| `URL` | 蓝湖项目链接（必填） |
| `--output` | 自定义输出目录 |
| `--no-slices` | 跳过切图下载 |
| `--no-preview` | 跳过预览图下载 |

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
  "timeout": 30
}
```

## 获取 Cookie 方法

1. 登录蓝湖网页版 (https://lanhuapp.com)
2. 按 F12 打开开发者工具
3. 切换到 Network 标签
4. 刷新页面，找到任意请求
5. 在 Headers 中找到 Cookie 字段
6. 复制完整的 Cookie 值

## 执行步骤

1. 读取配置文件 `.claude/lanhu.config.json`
2. 解析蓝湖 URL
3. 获取页面列表（Pages）
4. 获取每个页面的详情
5. 获取设计图列表（Designs）
6. 下载设计数据：Schema JSON + Sketch JSON + 预览图
7. 下载切图资源
8. 生成 README.md 和 meta.json

## 输出

数据保存到 `docs/lanhu/pages/{项目名}-{yyyyMMddHH}/`

```
{项目名}-{yyyyMMddHH}/
├── pages/           # 页面数据
│   └── {页面名}/
│       └── page.json
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

## 执行命令

执行 Python 脚本：

```bash
cd skills/export-lanhu/scripts
python export_lanhu.py "<URL>"
```

## 示例

导出蓝湖设计数据：

```bash
/export-lanhu "https://lanhuapp.com/web/#/item/project/product?tid=xxx&pid=xxx&docId=xxx"
```

指定输出目录：

```bash
/export-lanhu "https://lanhuapp.com/web/#/item/project/product?tid=xxx&pid=xxx" --output ./my-designs
```

跳过切图下载：

```bash
/export-lanhu "https://lanhuapp.com/..." --no-slices
```
