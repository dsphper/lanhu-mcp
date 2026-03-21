---
name: analyze-lanhu-design
description: 解析 export-lanhu 技能导出的设计数据（sketch.json），生成高质量的 UI 布局描述文档，包含层级树形图、区域示意图、 Flex 属性提示， 间距对齐信息和， 切图索引和样式汇总。 支持多框架参数化输出（html, vue, react, flutter, 小程序, UniApp）。 觏述时触发: 用户请求分析蓝湖设计、或蓝湖设计分析， 或提到蓝湖、 或关键词如 "analyze design"、"蓝湖设计分析", "解析 lanhu 设计" 等。
compatibility: Claude Code, Claude Desktop, Claude.ai
---

## 功能

- 解析 export-lanhu 导出的目录结构
- 生成层级树形图（可视化组件嵌套)
- 生成区域示意图 (ASCII 布局图)
- 分析 Flex 布局属性
- 生成间距对齐表格
- 提取设计变量（颜色、字体、间距)
- 生成切图索引

## 输入

- `export_dir`: export-lanhu 导出的目录路径
- `--framework`: 目标框架 (html/vue/react/flutter/miniprogram/uniapp)
- `--design`: 指定设计图名称
- `--output`: 自定义输出目录

