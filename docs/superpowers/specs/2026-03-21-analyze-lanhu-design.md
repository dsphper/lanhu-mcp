# analyze-lanhu-design 技能设计文档

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建一个 Claude Code Skill，解析 export-lanhu 输出的设计数据，生成高质量的 UI 布局描述文档，帮助 Claude Code 高质量还原页面。

**Architecture:** 混合方案 - Python 预处理脚本提取结构化数据，Claude 智能分析生成语义化组件描述。支持多框架参数化输出（HTML/Vue/React/Flutter/小程序/UniApp）。

**Tech Stack:** Python 3.10+, httpx (复用现有依赖), Markdown 输出

---

## 1. 概述

### 1.1 背景

export-lanhu 技能已能导出蓝湖设计数据（sketch.json、schema.json、预览图、切图）。但这些原始 JSON 数据需要进一步解析才能帮助 AI 高质量还原页面。

### 1.2 目标

创建 `analyze-lanhu-design` 技能，将原始设计数据转换为结构化的 UI 布局描述文档，包含：

1. **层级树形图** - 可视化展示组件嵌套关系
2. **区域示意图** - ASCII 布局图展示页面结构
3. **Flex 属性提示** - 推荐的 CSS Flex 布局属性
4. **间距对齐信息** - 详细的 margin/padding/alignment 数据
5. **切图索引** - 所有切图资源的路径和用途
6. **样式汇总** - 颜色、字体、间距等设计变量

### 1.3 用户故事

> 作为开发者，我希望导出蓝湖设计后，能快速获得结构化的布局描述文档，以便 Claude Code 能高质量还原页面，无需我手动分析原始 JSON。

---

## 2. 功能规格

### 2.1 输入

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `export_dir` | string | ✅ | export-lanhu 导出的目录路径 |
| `--framework` | string | - | 目标框架: html/vue/react/flutter/miniprogram/uniapp (默认: html) |
| `--design` | string | - | 指定设计图名称（可选，默认处理所有） |
| `--output` | string | - | 自定义输出目录（默认: {export_dir}/analysis/） |

### 2.2 输出

```
{export_dir}/analysis/
├── layout-analysis.md    # 主布局文档（每个设计图一个）
├── components.md         # 组件详细描述
├── slices.md             # 切图索引
└── styles.md             # 样式汇总（颜色、字体、间距）
```

### 2.3 输出文件内容

#### 2.3.1 layout-analysis.md

每个设计图生成一个布局分析文档，包含：

```markdown
# [设计图名称] - UI 布局分析

## 概览
- 设备、尺寸、主色调、设计工具

## 1. 层级树形图
- 树形结构展示组件嵌套关系
- 标注切图引用 [slice: xxx.png]

## 2. 区域示意图
- ASCII 布局图展示页面结构
- 标注间距和尺寸

## 3. Flex 属性提示
- 每个容器的推荐 Flex 属性

## 4. 间距对齐信息
- 外边距表格
- 内边距表格
- 对齐方式表格

## 5. 实现建议
- 推荐布局方案
- 注意事项
```

#### 2.3.2 components.md

```markdown
# 组件详细说明

## [组件名称]

### 基本信息
- 类型: 容器/文本/图片/按钮
- 尺寸: 宽 x 高
- 位置: left, top

### 样式属性
- 圆角: xxpx
- 背景: #XXXXXX
- 阴影: ...
- 边框: ...

### 内容
- 文本: "xxx"
- 图片: slices/xxx.png

### 子组件
- [子组件列表]
```

#### 2.3.3 slices.md

```markdown
# 切图资源索引

| 名称 | 路径 | 尺寸 | 格式 | 用途 |
|------|------|------|------|------|
| icon_back.png | slices/APP引导页/icon_back.png | 24x24 | PNG | 返回按钮 |
```

#### 2.3.4 styles.md

```markdown
# 设计样式汇总

## 颜色变量
| 名称 | 值 | 用途 |
|------|------|------|
| primary | #1A1A1A | 主色调 |

## 字体变量
| 名称 | 大小 | 行高 | 字重 | 用途 |
|------|------|------|------|------|
| title | 18px | 24px | Medium | 标题 |

## 间距变量
| 名称 | 值 | 用途 |
|------|------|------|
| padding-base | 16px | 基础内边距 |
```

---

## 3. 技术设计

### 3.1 文件结构

```
skills/analyze-lanhu-design/
├── SKILL.md                      # 技能说明文档
├── scripts/
│   ├── analyze_design.py         # 主入口脚本
│   ├── layer_parser.py           # 图层解析器
│   ├── layout_analyzer.py        # 布局分析器
│   ├── style_extractor.py        # 样式提取器
│   └── markdown_generator.py     # Markdown 生成器
└── references/
    ├── layer-types.md            # 图层类型参考
    └── framework-mappings.md     # 框架映射参考
```

### 3.2 核心模块

#### 3.2.1 layer_parser.py

**职责:** 解析 sketch.json 中的图层结构

**输入:** sketch.json 路径

**输出:** 结构化的图层树

```python
@dataclass
class Layer:
    id: str
    name: str
    type: str  # shapeLayer, textLayer, group, etc.
    frame: Frame
    style: Style
    children: list[Layer]
    # 特殊字段
    text: Optional[TextContent]
    image: Optional[ImageRef]

@dataclass
class Frame:
    left: int
    top: int
    width: int
    height: int

@dataclass
class Style:
    fills: list[Fill]
    borders: list[Border]
    shadows: list[Shadow]
    opacity: float
    radius: Radius
```

#### 3.2.2 layout_analyzer.py

**职责:** 分析图层布局关系，生成 Flex 属性建议

**核心逻辑:**

1. **识别容器类型:**
   - 水平排列 → `flex-direction: row`
   - 垂直排列 → `flex-direction: column`
   - 居中分布 → `justify-content: center`
   - 两端分布 → `justify-content: space-between`
   - 等距分布 → `justify-content: space-around`

2. **计算间距:**
   - 分析相邻元素的 gap
   - 提取统一的 padding 值

3. **生成布局树:**
   - 识别语义区域（Header、Content、Footer）
   - 生成分组建议

#### 3.2.3 style_extractor.py

**职责:** 提取并汇总设计样式变量

**输出:**
- 颜色变量表
- 字体变量表
- 间距变量表

#### 3.2.4 markdown_generator.py

**职责:** 生成最终 Markdown 文档

**支持的输出格式:**
- 层级树形图 (ASCII 树)
- 区域示意图 (ASCII 盒子)
- Flex 代码块
- Markdown 表格

### 3.3 数据流

```
sketch.json
    │
    ▼
┌─────────────────┐
│  layer_parser   │ → LayerTree
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ layout_analyzer │ → LayoutAnalysis
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ style_extractor │ → StyleVariables
└─────────────────┘
    │
    ▼
┌──────────────────┐
│ markdown_generator│ → .md files
└──────────────────┘
```

---

## 4. 框架适配

### 4.1 框架参数映射

| 框架 | 标识 | 组件语法 | 样式语法 |
|------|------|----------|----------|
| HTML | `html` | `<div>`, `<span>` | CSS |
| Vue | `vue` | `<template>`, `<script>` | Scoped CSS |
| React | `react` | JSX | CSS Modules / Styled |
| Flutter | `flutter` | Widget | Dart |
| 小程序 | `miniprogram` | `<view>`, `<text>` | WXSS |
| UniApp | `uniapp` | `<view>`, `<text>` | SCSS |

### 4.2 示例输出差异

#### HTML 输出
```css
.card-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
}
```

#### Flutter 输出
```dart
Column(
  children: [
    // cards...
  ],
)
// 使用 SizedBox(height: 16) 作为 gap
```

#### 小程序输出
```css
.card-container {
  display: flex;
  flex-direction: column;
}
.card-container > view:not(:last-child) {
  margin-bottom: 16px;
}
```

---

## 5. 边界情况处理

### 5.1 空数据处理
- schema.json 为空 → 跳过，仅使用 sketch.json
- 无切图 → slices.md 生成空表并提示

### 5.2 复杂图层处理
- 嵌套深度 > 10 → 警告并截断显示
- 图层数量 > 100 → 分页输出或摘要模式

### 5.3 错误处理
- 目录不存在 → 提示用户先运行 export-lanhu
- sketch.json 格式错误 → 报告具体错误位置

---

## 6. 使用示例

### 6.1 基本使用

```bash
/analyze-lanhu-design docs/lanhu/pages/MyProject-2026032023
```

### 6.2 指定框架

```bash
/analyze-lanhu-design docs/lanhu/pages/MyProject-2026032023 --framework flutter
```

### 6.3 分析单个设计

```bash
/analyze-lanhu-design docs/lanhu/pages/MyProject-2026032023 --design "首页"
```

---

## 7. 成功标准

1. **功能完整性**
   - [ ] 能正确解析 sketch.json 图层结构
   - [ ] 能生成层级树形图
   - [ ] 能生成区域示意图
   - [ ] 能生成 Flex 属性提示
   - [ ] 能生成间距对齐信息表
   - [ ] 能生成切图索引
   - [ ] 能生成样式汇总

2. **输出质量**
   - [ ] Markdown 格式正确，可被 Claude Code 理解
   - [ ] 布局建议合理，符合设计意图
   - [ ] 切图路径正确可访问

3. **多框架支持**
   - [ ] 支持 HTML 输出
   - [ ] 支持 Vue 输出
   - [ ] 支持 React 输出
   - [ ] 支持 Flutter 输出
   - [ ] 支持小程序输出
   - [ ] 支持 UniApp 输出

---

## 8. 后续扩展

- [ ] 支持直接传入蓝湖 URL（集成 export-lanhu）
- [ ] 支持增量分析（只分析变更的设计图）
- [ ] 支持导出为 PDF 格式
- [ ] 支持多语言输出
