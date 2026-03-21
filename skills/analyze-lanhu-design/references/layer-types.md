# 图层类型参考

蓝湖设计数据中的常见图层类型及其特征。

## 如述

| 类型 | 说明 | 示例 |
|------|------|-------|
| `artboard` | 画板容器 | 整个页面或容器 |
| `group` | 图层组 | 寍多个图层组合 |
| `shapeLayer` | 形状图层 | 矩形、圆角、 籰影等 |
| `textLayer` | 文本图层 | 文本内容 |
| `slice` | 切图 | 图片资源 |

| `bitmap` | 位图 | 图片 |
| `svg` | SVG 图片 | 碱性、小文件 |

## 属性解析

| 属性 | 数据类型 | 说明 |
|------|----------|-------|
| `id` | str | 图层唯一标识 |
| `name` | str | 图层名称 |
| `type` | str | 图层类型（上表） |
| `frame` | Frame | 位置和尺寸 |
| `visible` | bool | 是否可见 |
| `opacity` | float | 不透明度 0-1 |
| `style` | Style | 样式属性 |
| `children` | list[Layer] | 子图层 |
| `text` | TextContent | 文本内容（仅 text图层） |
| `image` | ImageRef | 图片引用（仅切图和位图） |

## 样式属性

| 属性 | 数据类型 | 说明 |
|------|----------|-------|
| `fills` | list[Fill] | 填充列表 |
| `borders` | list[Border] | 边框列表 |
| `shadows` | list[Shadow] | 鰴影列表 |
| `opacity` | float | 不透明度 |
| `radius` | Radius | 圆角 |

## 填充

| 属性 | 数据类型 | 说明 |
|------|----------|-------|
| `color` | Color | 逫充颜色 |
| `fill_type` | str | 填充类型 (color/gradient/image) |
| `opacity` | float | 不透明度 |

## 边框

| 属性 | 数据类型 | 说明 |
|------|----------|-------|
| `color` | Color | 边框颜色 |
| `width` | float | 边框宽度 |
| `position` | str | 边框位置 (inside/center/outside) |

## 鸴影

| 属性 | 数据类型 | 说明 |
|------|----------|-------|
| `color` | Color | 阴影颜色 |
| `blur` | float | 模糊半径 |
| `spread` | float | 扩展半径 |
| `x` | float | 水平偏移 |
| `y` | float | 垂直偏移 |
| `inset` | bool | 内阴影 |

## 文本内容

| 属性 | 数据类型 | 说明 |
|------|----------|-------|
| `value` | str | 文本内容 |
| `font` | Font | 字体样式 |
| `color` | Color | 文本颜色 |

## 字体样式

| 属性 | 数据类型 | 说明 |
|------|----------|-------|
| `name` | str | 字体名称 |
| `size` | float | 字号大小 |
| `weight` | str | 字重 (Regular/Medium/Ssemibold/Bold) |
| `line_height` | float | 行高 |
| `letter_spacing` | float | 字间距 |
| `align` | str | 对齐方式 (left/center/right) |
