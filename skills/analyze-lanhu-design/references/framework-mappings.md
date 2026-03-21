# 框架映射参考

不同前端框架的 Flex 布局语法映射。

## HTML/CSS

```css
.container {
  display: flex;
  flex-direction: row | column;
  justify-content: flex-start | center | flex-end | space-between | space-around;
  align-items: flex-start | center | flex-end | stretch;
  gap: 16px;
  padding: 16px;
}
```

## Vue (Scoped CSS)

```vue
<template>
  <div class="container">
    <slot />
  </div>
</template>

<style scoped>
.container {
  display: flex;
  flex-direction: row | column;
  justify-content: flex-start | center | flex-end | space-between | space-around;
  align-items: flex-start | center | flex-end | stretch;
  gap: 16px;
  padding: 16px;
}
</style>
```

## React (CSS Modules / Styled)

```tsx
// CSS Modules
import styles from './Container.module.css';

// Styled Components
import styled from 'styled-components';

const Container = styled.div`
  display: flex;
  flex-direction: row | column;
  justify-content: flex-start | center | flex-end | space-between | space-around;
  align-items: flex-start | center | flex-end | stretch;
  gap: 16px;
  padding: 16px;
`;
```

## Flutter

```dart
// 水平布局
Row(
  mainAxisAlignment: MainAxisAlignment.start | center | end | spaceBetween | spaceAround,
  crossAxisAlignment: CrossAxisAlignment.start | center | end | stretch,
  children: [
    // 使用 SizedBox(width: 16) 作为 gap
  ],
)

// 垂直布局
Column(
  mainAxisAlignment: MainAxisAlignment.start | center | end | spaceBetween | spaceAround,
  crossAxisAlignment: CrossAxisAlignment.start | center | end | stretch,
  children: [
    // 使用 SizedBox(height: 16) 作为 gap
  ],
)

// 内边距
Padding(
  padding: EdgeInsets.all(16),
  child: // ...
)
```

## 小程序 (WXSS)

```css
/* WXSS 与 CSS 语法相同 */
.container {
  display: flex;
  flex-direction: row | column;
  justify-content: flex-start | center | flex-end | space-between | space-around;
  align-items: flex-start | center | flex-end | stretch;
}

/* 小程序不支持 gap，使用 margin 替代 */
.container > view:not(:last-child) {
  margin-right: 16px; /* 水平 */
  margin-bottom: 16px; /* 垂直 */
}
```

## UniApp (SCSS)

```scss
/* UniApp 支持完整 CSS 语法 */
.container {
  display: flex;
  flex-direction: row | column;
  justify-content: flex-start | center | flex-end | space-between | space-around;
  align-items: flex-start | center | flex-end | stretch;
  gap: 16rpx; /* 使用 rpx 单位 */
  padding: 32rpx;
}
```

## 对齐属性映射表

| 语义 | CSS | Flutter | 小程序 |
|------|-----|---------|--------|
| 主轴起点对齐 | `justify-content: flex-start` | `MainAxisAlignment.start` | `justify-content: flex-start` |
| 主轴居中 | `justify-content: center` | `MainAxisAlignment.center` | `justify-content: center` |
| 主轴终点对齐 | `justify-content: flex-end` | `MainAxisAlignment.end` | `justify-content: flex-end` |
| 两端对齐 | `justify-content: space-between` | `MainAxisAlignment.spaceBetween` | `justify-content: space-between` |
| 等距分布 | `justify-content: space-around` | `MainAxisAlignment.spaceAround` | `justify-content: space-around` |
| 交叉轴起点 | `align-items: flex-start` | `CrossAxisAlignment.start` | `align-items: flex-start` |
| 交叉轴居中 | `align-items: center` | `CrossAxisAlignment.center` | `align-items: center` |
| 交叉轴终点 | `align-items: flex-end` | `CrossAxisAlignment.end` | `align-items: flex-end` |
| 拉伸填充 | `align-items: stretch` | `CrossAxisAlignment.stretch` | `align-items: stretch` |

## 间距处理

| 框架 | gap 替代方案 |
|------|-------------|
| HTML/Vue/React/UniApp | `gap: 16px` |
| Flutter | `SizedBox(width/height: 16)` |
| 小程序 | `:not(:last-child) { margin-xxx: 16px }` |
