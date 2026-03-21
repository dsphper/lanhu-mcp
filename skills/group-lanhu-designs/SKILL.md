---
name: group-lanhu-designs
description: 将蓝湖设计数据中相关联的页面（主页面+弹窗+状态变体）分组并合并分析，生成合并后的布局文档和切图资源。触发词：分组蓝湖设计、合并蓝湖页面、group lanhu、页面归类。
compatibility: Claude Code
---

## 功能

- 自动识别页面命名规则，将相关页面分组
- 支持业务顺序前缀（如 01_、02_）
- 支持状态变体识别（如 -展开、-收起）
- 支持弹窗/子页面识别（如 _–_隐私弹窗）
- 合并同名切图，保留最大尺寸
- 生成合并后的 Markdown 分析文档

## 命名规则

| 规则 | 模式 | 示例 |
|------|------|------|
| 业务顺序 | `数字_名称` | 01_登录 |
| 状态后缀 | `名称-状态` | 登录-展开 |
| 子页面 | `名称_-_子页面` | 登录_-_隐私弹窗 |
| 数字变体 | `名称数字` | 识别提示1 |

## 使用方法

```bash
# 基本用法
python skills/group-lanhu-designs/scripts/group_designs.py "docs/lanhu/pages/MyProject"

# 指定框架
python skills/group-lanhu-designs/scripts/group_designs.py "docs/lanhu/pages/MyProject" --framework flutter

# 不合并切图
python skills/group-lanhu-designs/scripts/group_designs.py "docs/lanhu/pages/MyProject" --no-slices

# 自定义输出目录
python skills/group-lanhu-designs/scripts/group_designs.py "docs/lanhu/pages/MyProject" --output "./output"
```

## 输出

```
docs/lanhu/pages/MyProject/
└── grouped/
    ├── 01_登录/
    │   ├── 登录-合并分析.md
    │   └── slices/
    └── 02_首页/
        ├── 首页-合并分析.md
        └── slices/
```

## 依赖

- Python 3.10+
- Pillow (PIL) - 用于读取图片尺寸
