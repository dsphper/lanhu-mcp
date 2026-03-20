# analyze-lanhu-design 实现计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建 analyze-lanhu-design 技能，解析 export-lanhu 输出的 sketch.json，生成包含层级树、区域示意图、Flex 属性、间距对齐信息的 Markdown 文档。

**Architecture:** 模块化 Python 脚本 - 数据模型 → 图层解析 → 布局分析 → 样式提取 → Markdown 生成。每个模块职责单一，通过数据类传递数据。

**Tech Stack:** Python 3.10+, dataclasses, argparse, pathlib

---

## 文件结构

```
skills/analyze-lanhu-design/
├── SKILL.md                          # 技能文档
├── scripts/
│   ├── analyze_design.py             # 主入口 (CLI)
│   ├── models.py                     # 数据模型定义
│   ├── layer_parser.py               # sketch.json 解析
│   ├── layout_analyzer.py            # 布局分析
│   ├── style_extractor.py            # 样式提取
│   └── markdown_generator.py         # Markdown 生成
└── references/
    ├── layer-types.md                # 图层类型参考
    └── framework-mappings.md         # 框架映射参考
```

---

## Task 1: 数据模型层 (models.py)

**Files:**
- Create: `skills/analyze-lanhu-design/scripts/models.py`

- [ ] **Step 1: 创建数据模型文件**

```python
"""
analyze-lanhu-design 数据模型定义
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Frame:
    """位置和尺寸"""
    left: int
    top: int
    width: int
    height: int


@dataclass
class Radius:
    """圆角"""
    top_left: int = 0
    top_right: int = 0
    bottom_left: int = 0
    bottom_right: int = 0


@dataclass
class Color:
    """颜色"""
    r: int
    g: int
    b: int
    a: float
    value: str  # rgba(x,x,x,x)

    def to_hex(self) -> str:
        """转换为十六进制"""
        return f"#{self.r:02X}{self.g:02X}{self.b:02X}"


@dataclass
class Fill:
    """填充"""
    color: Optional[Color]
    opacity: float
    fill_type: str  # color, gradient, image


@dataclass
class Border:
    """边框"""
    color: Color
    width: int
    position: str


@dataclass
class Shadow:
    """阴影"""
    color: Color
    blur: int
    spread: int
    x: int
    y: int
    inset: bool


@dataclass
class Font:
    """字体"""
    name: str
    size: int
    weight: str  # Regular, Medium, Bold, etc.
    line_height: int
    letter_spacing: int
    align: str  # left, center, right


@dataclass
class TextContent:
    """文本内容"""
    value: str
    font: Font
    color: Color


@dataclass
class ImageRef:
    """图片引用"""
    url: str
    format: str  # png, svg


@dataclass
class Style:
    """样式"""
    fills: list[Fill] = field(default_factory=list)
    borders: list[Border] = field(default_factory=list)
    shadows: list[Shadow] = field(default_factory=list)
    opacity: float = 1.0
    radius: Optional[Radius] = None
    blend_mode: int = 0


@dataclass
class Layer:
    """图层"""
    id: str
    name: str
    type: str  # shapeLayer, textLayer, group, etc.
    frame: Frame
    style: Optional[Style] = None
    children: list['Layer'] = field(default_factory=list)
    text: Optional[TextContent] = None
    image: Optional[ImageRef] = None
    visible: bool = True
    opacity: float = 1.0


@dataclass
class LayoutHint:
    """布局提示"""
    direction: str  # row, column
    justify: str  # flex-start, center, space-between, space-around
    align: str  # flex-start, center, stretch
    gap: int
    padding: tuple[int, int, int, int]  # top, right, bottom, left


@dataclass
class DesignAnalysis:
    """设计分析结果"""
    name: str
    device: str
    width: int
    height: int
    layers: list[Layer]
    layout_hints: dict[str, LayoutHint]  # layer_id -> hint
    colors: list[tuple[str, str]]  # (name, hex value)
    fonts: list[tuple[str, Font]]  # (name, font)
    slices: list[tuple[str, str, int, int]]  # (name, path, width, height)
```

- [ ] **Step 2: 验证模块可导入**

```bash
cd E:/xen/code/claude/project/lanhu-mcp/skills/analyze-lanhu-design/scripts && python -c "from models import Layer, Frame; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add skills/analyze-lanhu-design/scripts/models.py
git commit -m "feat(analyze): add data models for layer, style, and layout"
```

---

## Task 2: 图层解析器 (layer_parser.py)

**Files:**
- Create: `skills/analyze-lanhu-design/scripts/layer_parser.py`

- [ ] **Step 1: 创建图层解析器**

```python
"""
sketch.json 解析器
"""
import json
from pathlib import Path
from models import (
    Layer, Frame, Style, Fill, Border, Shadow, Color,
    Radius, TextContent, Font, ImageRef
)


class LayerParser:
    """解析 sketch.json 为 Layer 树"""

    def __init__(self, sketch_path: str | Path):
        self.sketch_path = Path(sketch_path)
        self.data = self._load_json()

    def _load_json(self) -> dict:
        with open(self.sketch_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def parse(self) -> Layer:
        """解析返回根图层"""
        artboard = self.data.get('artboard', {})
        return self._parse_layer(artboard)

    def _parse_layer(self, data: dict) -> Layer:
        """递归解析图层"""
        layer = Layer(
            id=data.get('id', ''),
            name=data.get('name', 'unnamed'),
            type=data.get('type', 'unknown'),
            frame=self._parse_frame(data.get('frame', {})),
            visible=data.get('visible', True),
            opacity=data.get('opacity', 1.0)
        )

        # 解析样式
        if 'style' in data:
            layer.style = self._parse_style(data['style'])

        # 解析文本
        if data.get('type') == 'textLayer' and 'text' in data:
            layer.text = self._parse_text(data['text'])

        # 解析图片
        if 'image' in data:
            img = data['image']
            layer.image = ImageRef(
                url=img.get('imageUrl') or img.get('svgUrl', ''),
                format='svg' if img.get('svgUrl') else 'png'
            )

        # 递归解析子图层
        for child_data in data.get('layers', []):
            child = self._parse_layer(child_data)
            layer.children.append(child)

        return layer

    def _parse_frame(self, data: dict) -> Frame:
        return Frame(
            left=int(data.get('left', 0)),
            top=int(data.get('top', 0)),
            width=int(data.get('width', 0)),
            height=int(data.get('height', 0))
        )

    def _parse_style(self, data: dict) -> Style:
        style = Style(opacity=data.get('opacity', 1.0))

        # 圆角
        if 'radius' in data:
            r = data['radius']
            if isinstance(r, dict):
                style.radius = Radius(
                    top_left=r.get('topLeft', 0),
                    top_right=r.get('topRight', 0),
                    bottom_left=r.get('bottomLeft', 0),
                    bottom_right=r.get('bottomRight', 0)
                )

        # 填充
        for fill_data in data.get('fills', []):
            if fill_data.get('type') == 'color' and 'color' in fill_data:
                style.fills.append(Fill(
                    color=self._parse_color(fill_data['color']),
                    opacity=fill_data.get('opacity', 1.0),
                    fill_type='color'
                ))

        # 边框
        for border_data in data.get('borders', []):
            if 'color' in border_data:
                style.borders.append(Border(
                    color=self._parse_color(border_data['color']),
                    width=border_data.get('width', 1),
                    position=border_data.get('position', 'inside')
                ))

        # 阴影
        for shadow_data in data.get('shadows', []):
            if 'color' in shadow_data:
                style.shadows.append(Shadow(
                    color=self._parse_color(shadow_data['color']),
                    blur=shadow_data.get('blur', 0),
                    spread=shadow_data.get('spread', 0),
                    x=shadow_data.get('x', 0),
                    y=shadow_data.get('y', 0),
                    inset=shadow_data.get('inset', False)
                ))

        return style

    def _parse_color(self, data: dict) -> Color:
        return Color(
            r=data.get('r', 0),
            g=data.get('g', 0),
            b=data.get('b', 0),
            a=data.get('a', 1.0),
            value=data.get('value', '')
        )

    def _parse_text(self, data: dict) -> TextContent:
        style = data.get('style', {})
        font_data = style.get('font', {})

        font = Font(
            name=font_data.get('name', 'sans-serif'),
            size=font_data.get('size', 14),
            weight=font_data.get('type', 'Regular'),
            line_height=font_data.get('lineSpacing', font_data.get('lineHeight', {}).get('value', 20)),
            letter_spacing=font_data.get('letterSpacing', {}).get('value', 0),
            align=font_data.get('align', 'left')
        )

        color_data = style.get('color', {})
        color = self._parse_color(color_data) if color_data else Color(0, 0, 0, 1, '')

        return TextContent(
            value=data.get('value', ''),
            font=font,
            color=color
        )

    def get_meta(self) -> dict:
        """获取元信息"""
        return self.data.get('meta', {})
```

- [ ] **Step 2: 测试解析器**

```bash
cd E:/xen/code/claude/project/lanhu-mcp/skills/analyze-lanhu-design/scripts && python -c "
from layer_parser import LayerParser
parser = LayerParser('../../../docs/lanhu/pages/DesignProject-da907f83-2026032023/designs/便捷提货/sketch.json')
layer = parser.parse()
print(f'Root: {layer.name}, Children: {len(layer.children)}')
"
```

Expected: `Root: artboard name, Children: N`

- [ ] **Step 3: Commit**

```bash
git add skills/analyze-lanhu-design/scripts/layer_parser.py
git commit -m "feat(analyze): add layer parser for sketch.json"
```

---

## Task 3: 布局分析器 (layout_analyzer.py)

**Files:**
- Create: `skills/analyze-lanhu-design/scripts/layout_analyzer.py`

- [ ] **Step 1: 创建布局分析器**

```python
"""
布局分析器 - 分析图层排列模式，生成 Flex 属性建议
"""
from models import Layer, LayoutHint, Frame
from typing import Optional
from collections import Counter


class LayoutAnalyzer:
    """分析图层布局关系"""

    def __init__(self, root: Layer):
        self.root = root
        self.hints: dict[str, LayoutHint] = {}
        self._analyze(root)

    def _analyze(self, layer: Layer):
        """递归分析图层"""
        if not layer.children:
            return

        # 分析当前图层的子元素布局
        hint = self._detect_layout(layer)
        if hint:
            self.hints[layer.id] = hint

        # 递归分析子图层
        for child in layer.children:
            self._analyze(child)

    def _detect_layout(self, layer: Layer) -> Optional[LayoutHint]:
        """检测布局模式"""
        children = [c for c in layer.children if c.visible]
        if len(children) < 2:
            return None

        # 获取所有子元素的位置信息
        frames = [c.frame for c in children]

        # 判断是水平还是垂直排列
        horizontal_overlap = self._calc_horizontal_overlap(frames)
        vertical_overlap = self._calc_vertical_overlap(frames)

        if horizontal_overlap > 0.5 and vertical_overlap < 0.3:
            # 垂直排列
            direction = 'column'
            gap = self._calc_vertical_gap(frames)
        elif vertical_overlap > 0.5 and horizontal_overlap < 0.3:
            # 水平排列
            direction = 'row'
            gap = self._calc_horizontal_gap(frames)
        else:
            # 复杂布局，默认垂直
            direction = 'column'
            gap = 0

        # 分析对齐方式
        justify = self._detect_justify(layer.frame, frames, direction)
        align = self._detect_align(layer.frame, frames, direction)

        # 计算内边距
        padding = self._calc_padding(layer.frame, frames)

        return LayoutHint(
            direction=direction,
            justify=justify,
            align=align,
            gap=gap,
            padding=padding
        )

    def _calc_horizontal_overlap(self, frames: list[Frame]) -> float:
        """计算水平重叠率"""
        if len(frames) < 2:
            return 1.0

        overlaps = []
        for i in range(len(frames) - 1):
            f1, f2 = frames[i], frames[i + 1]
            # 检查垂直位置是否有重叠
            top_max = max(f1.top, f2.top)
            bottom_min = min(f1.top + f1.height, f2.top + f2.height)
            if bottom_min > top_max:
                overlap = (bottom_min - top_max) / min(f1.height, f2.height)
                overlaps.append(overlap)
            else:
                overlaps.append(0)

        return sum(overlaps) / len(overlaps) if overlaps else 0

    def _calc_vertical_overlap(self, frames: list[Frame]) -> float:
        """计算垂直重叠率"""
        if len(frames) < 2:
            return 1.0

        overlaps = []
        for i in range(len(frames) - 1):
            f1, f2 = frames[i], frames[i + 1]
            # 检查水平位置是否有重叠
            left_max = max(f1.left, f2.left)
            right_min = min(f1.left + f1.width, f2.left + f2.width)
            if right_min > left_max:
                overlap = (right_min - left_max) / min(f1.width, f2.width)
                overlaps.append(overlap)
            else:
                overlaps.append(0)

        return sum(overlaps) / len(overlaps) if overlaps else 0

    def _calc_vertical_gap(self, frames: list[Frame]) -> int:
        """计算垂直间距"""
        if len(frames) < 2:
            return 0

        gaps = []
        sorted_frames = sorted(frames, key=lambda f: f.top)
        for i in range(len(sorted_frames) - 1):
            f1, f2 = sorted_frames[i], sorted_frames[i + 1]
            gap = f2.top - (f1.top + f1.height)
            if gap > 0:
                gaps.append(gap)

        return self._most_common(gaps) if gaps else 0

    def _calc_horizontal_gap(self, frames: list[Frame]) -> int:
        """计算水平间距"""
        if len(frames) < 2:
            return 0

        gaps = []
        sorted_frames = sorted(frames, key=lambda f: f.left)
        for i in range(len(sorted_frames) - 1):
            f1, f2 = sorted_frames[i], sorted_frames[i + 1]
            gap = f2.left - (f1.left + f1.width)
            if gap > 0:
                gaps.append(gap)

        return self._most_common(gaps) if gaps else 0

    def _most_common(self, values: list[int]) -> int:
        """取最常见的值（允许±2的误差）"""
        if not values:
            return 0
        counter = Counter(values)
        return counter.most_common(1)[0][0]

    def _detect_justify(self, container: Frame, frames: list[Frame], direction: str) -> str:
        """检测主轴对齐方式"""
        if direction == 'row':
            # 检查水平分布
            total_width = sum(f.width for f in frames)
            gaps = self._calc_horizontal_gap(frames)
            total_gaps = gaps * (len(frames) - 1)
            space_left = container.width - total_width - total_gaps - frames[0].left

            if abs(space_left - frames[0].left) < 5:
                return 'space-between'
            elif frames[0].left > 30:
                return 'center'
            else:
                return 'flex-start'
        else:
            # 检查垂直分布
            total_height = sum(f.height for f in frames)
            gaps = self._calc_vertical_gap(frames)
            total_gaps = gaps * (len(frames) - 1)
            space_top = frames[0].top
            space_bottom = container.height - (frames[-1].top + frames[-1].height)

            if abs(space_top - space_bottom) < 5 and space_top > 20:
                return 'space-between'
            elif abs(space_top - space_bottom) < 5:
                return 'center'
            else:
                return 'flex-start'

    def _detect_align(self, container: Frame, frames: list[Frame], direction: str) -> str:
        """检测交叉轴对齐方式"""
        if direction == 'row':
            # 检查垂直对齐
            centers = [f.top + f.height / 2 for f in frames]
            if all(abs(c - centers[0]) < 5 for c in centers):
                return 'center'
            elif all(f.top == frames[0].top for f in frames):
                return 'flex-start'
            else:
                return 'stretch'
        else:
            # 检查水平对齐
            centers = [f.left + f.width / 2 for f in frames]
            if all(abs(c - centers[0]) < 5 for c in centers):
                return 'center'
            elif all(f.left == frames[0].left for f in frames):
                return 'flex-start'
            else:
                return 'stretch'

    def _calc_padding(self, container: Frame, frames: list[Frame]) -> tuple[int, int, int, int]:
        """计算内边距"""
        if not frames:
            return (0, 0, 0, 0)

        top = min(f.top for f in frames)
        left = min(f.left for f in frames)
        bottom = container.height - max(f.top + f.height for f in frames)
        right = container.width - max(f.left + f.width for f in frames)

        return (top, right, bottom, left)

    def get_hint(self, layer_id: str) -> Optional[LayoutHint]:
        """获取指定图层的布局提示"""
        return self.hints.get(layer_id)

    def get_all_hints(self) -> dict[str, LayoutHint]:
        """获取所有布局提示"""
        return self.hints
```

- [ ] **Step 2: 测试布局分析器**

```bash
cd E:/xen/code/claude/project/lanhu-mcp/skills/analyze-lanhu-design/scripts && python -c "
from layer_parser import LayerParser
from layout_analyzer import LayoutAnalyzer
parser = LayerParser('../../../docs/lanhu/pages/DesignProject-da907f83-2026032023/designs/便捷提货/sketch.json')
root = parser.parse()
analyzer = LayoutAnalyzer(root)
print(f'Layout hints: {len(analyzer.get_all_hints())}')
"
```

Expected: `Layout hints: N`

- [ ] **Step 3: Commit**

```bash
git add skills/analyze-lanhu-design/scripts/layout_analyzer.py
git commit -m "feat(analyze): add layout analyzer with Flex detection"
```

---

## Task 4: 样式提取器 (style_extractor.py)

**Files:**
- Create: `skills/analyze-lanhu-design/scripts/style_extractor.py`

- [ ] **Step 1: 创建样式提取器**

```python
"""
样式提取器 - 提取颜色、字体、间距变量
"""
from models import Layer, Style, Color, Font
from collections import Counter
from typing import Optional


class StyleExtractor:
    """提取设计样式变量"""

    def __init__(self, root: Layer):
        self.root = root
        self.colors: list[tuple[str, str, int]] = []  # (name, hex, count)
        self.fonts: list[tuple[str, Font, int]] = []  # (name, font, count)
        self.spacings: list[tuple[str, int, int]] = []  # (name, value, count)
        self._extract(root)

    def _extract(self, layer: Layer):
        """递归提取样式"""
        # 提取填充颜色
        if layer.style and layer.style.fills:
            for fill in layer.style.fills:
                if fill.color and fill.fill_type == 'color':
                    self._add_color(fill.color)

        # 提取文本样式
        if layer.text:
            self._add_font(layer.text.font)
            self._add_color(layer.text.color)

        # 递归处理子图层
        for child in layer.children:
            self._extract(child)

    def _add_color(self, color: Optional[Color]):
        """添加颜色"""
        if not color:
            return

        hex_value = color.to_hex()
        # 查找是否已存在
        for i, (name, existing_hex, count) in enumerate(self.colors):
            if existing_hex == hex_value:
                self.colors[i] = (name, hex_value, count + 1)
                return

        # 生成名称
        name = self._generate_color_name(hex_value)
        self.colors.append((name, hex_value, 1))

    def _generate_color_name(self, hex_value: str) -> str:
        """生成颜色名称"""
        # 简单的颜色名称映射
        color_names = {
            '#FFFFFF': 'white',
            '#000000': 'black',
            '#1A1A1A': 'text-primary',
            '#333333': 'text-secondary',
            '#666666': 'text-tertiary',
            '#999999': 'text-placeholder',
            '#F5F5F5': 'bg-light',
            '#EEEEEE': 'bg-gray',
            '#1890FF': 'primary',
            '#52C41A': 'success',
            '#FAAD14': 'warning',
            '#FF4D4F': 'danger',
        }
        return color_names.get(hex_value, f'color-{hex_value[1:]}')

    def _add_font(self, font: Font):
        """添加字体"""
        # 使用 font-size-weight 作为唯一标识
        font_key = f'{font.name}-{font.size}-{font.weight}'

        for i, (name, existing_font, count) in enumerate(self.fonts):
            existing_key = f'{existing_font.name}-{existing_font.size}-{existing_font.weight}'
            if existing_key == font_key:
                self.fonts[i] = (name, existing_font, count + 1)
                return

        # 生成名称
        name = self._generate_font_name(font)
        self.fonts.append((name, font, 1))

    def _generate_font_name(self, font: Font) -> str:
        """生成字体名称"""
        size_name = {
            12: 'xs',
            13: 'sm',
            14: 'base',
            15: 'md',
            16: 'lg',
            18: 'xl',
            20: '2xl',
            24: '3xl',
            28: '4xl',
            32: '5xl',
        }.get(font.size, f'size-{font.size}')

        weight_name = {
            'Regular': '',
            'Medium': '-medium',
            'Semibold': '-semibold',
            'Bold': '-bold',
            'Heavy': '-heavy',
        }.get(font.weight, f'-{font.weight.lower()}')

        return f'text-{size_name}{weight_name}'

    def get_top_colors(self, limit: int = 20) -> list[tuple[str, str]]:
        """获取使用最多的颜色"""
        sorted_colors = sorted(self.colors, key=lambda x: x[2], reverse=True)
        return [(name, hex_val) for name, hex_val, _ in sorted_colors[:limit]]

    def get_top_fonts(self, limit: int = 20) -> list[tuple[str, Font]]:
        """获取使用最多的字体"""
        sorted_fonts = sorted(self.fonts, key=lambda x: x[2], reverse=True)
        return [(name, font) for name, font, _ in sorted_fonts[:limit]]
```

- [ ] **Step 2: 测试样式提取器**

```bash
cd E:/xen/code/claude/project/lanhu-mcp/skills/analyze-lanhu-design/scripts && python -c "
from layer_parser import LayerParser
from style_extractor import StyleExtractor
parser = LayerParser('../../../docs/lanhu/pages/DesignProject-da907f83-2026032023/designs/便捷提货/sketch.json')
root = parser.parse()
extractor = StyleExtractor(root)
print(f'Colors: {len(extractor.colors)}, Fonts: {len(extractor.fonts)}')
print(f'Top colors: {extractor.get_top_colors(3)}')
"
```

Expected: 显示颜色和字体数量

- [ ] **Step 3: Commit**

```bash
git add skills/analyze-lanhu-design/scripts/style_extractor.py
git commit -m "feat(analyze): add style extractor for colors and fonts"
```

---

## Task 5: Markdown 生成器 (markdown_generator.py)

**Files:**
- Create: `skills/analyze-lanhu-design/scripts/markdown_generator.py`

- [ ] **Step 1: 创建 Markdown 生成器**

```python
"""
Markdown 生成器 - 生成布局分析文档
"""
from models import Layer, LayoutHint, DesignAnalysis, Font
from layout_analyzer import LayoutAnalyzer
from style_extractor import StyleExtractor
from pathlib import Path


class MarkdownGenerator:
    """生成 Markdown 文档"""

    FRAMEWORK_SYNTAX = {
        'html': {
            'container': 'div',
            'text': 'span',
            'image': 'img',
            'flex_prefix': '',
        },
        'vue': {
            'container': 'div',
            'text': 'span',
            'image': 'img',
            'flex_prefix': '',
        },
        'react': {
            'container': 'div',
            'text': 'span',
            'image': 'img',
            'flex_prefix': '',
        },
        'flutter': {
            'container': 'Container',
            'text': 'Text',
            'image': 'Image',
            'flex_prefix': '// ',
        },
        'miniprogram': {
            'container': 'view',
            'text': 'text',
            'image': 'image',
            'flex_prefix': '',
        },
        'uniapp': {
            'container': 'view',
            'text': 'text',
            'image': 'image',
            'flex_prefix': '',
        },
    }

    def __init__(self, framework: str = 'html'):
        self.framework = framework
        self.syntax = self.FRAMEWORK_SYNTAX.get(framework, self.FRAMEWORK_SYNTAX['html'])

    def generate_layout_analysis(self, layer: Layer, analyzer: LayoutAnalyzer,
                                   extractor: StyleExtractor, meta: dict) -> str:
        """生成布局分析文档"""
        sections = [
            self._generate_header(layer, meta),
            self._generate_tree_diagram(layer),
            self._generate_area_diagram(layer),
            self._generate_flex_hints(layer, analyzer),
            self._generate_spacing_tables(layer, analyzer),
            self._generate_implementation_tips(layer, analyzer),
        ]
        return '\n\n'.join(sections)

    def _generate_header(self, layer: Layer, meta: dict) -> str:
        """生成文档头部"""
        device = meta.get('device', 'Unknown')
        return f"""# {layer.name} - UI 布局分析

## 概览
- **设备**: {device}
- **尺寸**: {layer.frame.width} x {layer.frame.height}
- **设计工具**: {meta.get('host', {}).get('name', 'Unknown')}
- **图层深度**: {self._calc_depth(layer)}"""

    def _calc_depth(self, layer: Layer, current: int = 0) -> int:
        """计算最大深度"""
        if not layer.children:
            return current
        return max(self._calc_depth(c, current + 1) for c in layer.children)

    def _generate_tree_diagram(self, layer: Layer, indent: int = 0) -> str:
        """生成层级树形图"""
        lines = ['## 1. 层级树形图', '', '```']

        def render_tree(l: Layer, prefix: str = ''):
            icon = '├── ' if indent > 0 else ''
            # 图层信息
            info = f'{l.name} ({l.frame.width}x{l.frame.height})'

            # 添加切图标记
            if l.image:
                info += f' [slice: {l.name}.{l.image.format}]'

            # 添加文本标记
            if l.text:
                text_preview = l.text.value[:20] + '...' if len(l.text.value) > 20 else l.text.value
                info += f' "{text_preview}"'

            lines.append(f'{prefix}{icon}{info}')

            # 递归子元素
            for i, child in enumerate(l.children):
                if child.visible:
                    is_last = i == len(l.children) - 1
                    child_prefix = prefix + ('    ' if is_last else '│   ')
                    render_tree(child, child_prefix)

        render_tree(layer)
        lines.append('```')
        return '\n'.join(lines)

    def _generate_area_diagram(self, layer: Layer) -> str:
        """生成区域示意图（简化版）"""
        lines = ['## 2. 区域示意图', '', '```']

        width = layer.frame.width
        height = layer.frame.height

        # 简化的 ASCII 布局图
        box_width = min(40, width // 10)
        box_height = min(15, height // 50)

        # 外框
        lines.append('┌' + '─' * box_width + '┐')

        # 渲染子元素
        visible_children = [c for c in layer.children if c.visible]
        if visible_children:
            for child in visible_children[:5]:  # 最多显示5个
                rel_top = (child.frame.top - layer.frame.top) / height
                rel_height = child.frame.height / height
                row_count = max(1, int(rel_height * box_height))

                child_width = int((child.frame.width / width) * box_width)
                child_width = max(5, min(child_width, box_width - 4))

                for _ in range(row_count):
                    lines.append('│ ' + '─' * child_width + ' ' * (box_width - child_width - 2) + ' │')

                # 标注
                label = child.name[:child_width - 2] if len(child.name) > child_width - 2 else child.name
                lines.append(f'│ [{label}]' + ' ' * (box_width - len(label) - 4) + ' │')

        lines.append('└' + '─' * box_width + '┘')
        lines.append('```')
        return '\n'.join(lines)

    def _generate_flex_hints(self, layer: Layer, analyzer: LayoutAnalyzer) -> str:
        """生成 Flex 属性提示"""
        lines = ['## 3. Flex 属性提示', '']

        def render_hints(l: Layer, path: str = ''):
            hint = analyzer.get_hint(l.id)
            if hint:
                section_name = path + l.name if path else l.name
                lines.append(f'### {section_name}')

                if self.framework == 'flutter':
                    lines.append('```dart')
                    if hint.direction == 'column':
                        lines.append('Column(')
                        lines.append('  children: [')
                        lines.append('    // children here')
                        lines.append('  ],')
                        lines.append(f') // gap: {hint.gap}px via SizedBox(height: {hint.gap})')
                    else:
                        lines.append('Row(')
                        lines.append('  children: [')
                        lines.append('    // children here')
                        lines.append('  ],')
                        lines.append(f') // gap: {hint.gap}px via SizedBox(width: {hint.gap})')
                    lines.append('```')
                else:
                    lines.append('```css')
                    lines.append(f'display: flex;')
                    lines.append(f'flex-direction: {hint.direction};')
                    lines.append(f'justify-content: {hint.justify};')
                    lines.append(f'align-items: {hint.align};')
                    if hint.gap > 0:
                        lines.append(f'gap: {hint.gap}px;')
                    if hint.padding != (0, 0, 0, 0):
                        p = hint.padding
                        lines.append(f'padding: {p[0]}px {p[1]}px {p[2]}px {p[3]}px;')
                    lines.append('```')
                lines.append('')

            for child in l.children:
                if child.visible:
                    render_hints(child, path + l.name + '/')

        render_hints(layer)
        return '\n'.join(lines)

    def _generate_spacing_tables(self, layer: Layer, analyzer: LayoutAnalyzer) -> str:
        """生成间距表格"""
        lines = ['## 4. 间距对齐信息', '']

        # 外边距表
        lines.append('### 外边距')
        lines.append('| 元素 | margin-top | margin-left | margin-right | margin-bottom |')
        lines.append('|------|------------|-------------|--------------|---------------|')

        for child in layer.children[:10]:  # 最多10个
            if child.visible:
                mt = child.frame.top - layer.frame.top
                ml = child.frame.left - layer.frame.left
                mb = layer.frame.height - (child.frame.top + child.frame.height - layer.frame.top)
                mr = layer.frame.width - (child.frame.left + child.frame.width - layer.frame.left)
                lines.append(f'| {child.name[:20]} | {mt}px | {ml}px | {mr}px | {mb}px |')

        lines.append('')
        return '\n'.join(lines)

    def _generate_implementation_tips(self, layer: Layer, analyzer: LayoutAnalyzer) -> str:
        """生成实现建议"""
        hints = analyzer.get_all_hints()

        column_count = sum(1 for h in hints.values() if h.direction == 'column')
        row_count = sum(1 for h in hints.values() if h.direction == 'row')

        return f"""## 5. 实现建议

### 推荐布局方案
- 主布局: Flex Column
- 垂直容器: {column_count} 个
- 水平容器: {row_count} 个

### 注意事项
1. 切图路径使用相对路径引用
2. 文本内容保持与设计一致
3. 注意适配不同屏幕尺寸"""

    def generate_slices_md(self, slices: list[tuple[str, str, int, int]]) -> str:
        """生成切图索引文档"""
        lines = ['# 切图资源索引', '', '| 名称 | 路径 | 尺寸 | 格式 |', '|------|------|------|------|']

        for name, path, width, height in slices:
            fmt = path.split('.')[-1].upper()
            lines.append(f'| {name} | {path} | {width}x{height} | {fmt} |')

        return '\n'.join(lines)

    def generate_styles_md(self, colors: list[tuple[str, str]],
                           fonts: list[tuple[str, Font]]) -> str:
        """生成样式汇总文档"""
        lines = ['# 设计样式汇总', '']

        # 颜色表
        lines.append('## 颜色变量')
        lines.append('| 名称 | 值 | 用途 |')
        lines.append('|------|------|------|')
        for name, hex_val in colors:
            lines.append(f'| {name} | {hex_val} | - |')

        lines.append('')

        # 字体表
        lines.append('## 字体变量')
        lines.append('| 名称 | 大小 | 行高 | 字重 | 用途 |')
        lines.append('|------|------|------|------|------|')
        for name, font in fonts:
            lines.append(f'| {name} | {font.size}px | {font.line_height}px | {font.weight} | - |')

        return '\n'.join(lines)
```

- [ ] **Step 2: 测试 Markdown 生成器**

```bash
cd E:/xen/code/claude/project/lanhu-mcp/skills/analyze-lanhu-design/scripts && python -c "
from layer_parser import LayerParser
from layout_analyzer import LayoutAnalyzer
from style_extractor import StyleExtractor
from markdown_generator import MarkdownGenerator
parser = LayerParser('../../../docs/lanhu/pages/DesignProject-da907f83-2026032023/designs/便捷提货/sketch.json')
root = parser.parse()
analyzer = LayoutAnalyzer(root)
extractor = StyleExtractor(root)
gen = MarkdownGenerator()
md = gen.generate_layout_analysis(root, analyzer, extractor, parser.get_meta())
print(md[:500])
"
```

Expected: 输出 Markdown 内容

- [ ] **Step 3: Commit**

```bash
git add skills/analyze-lanhu-design/scripts/markdown_generator.py
git commit -m "feat(analyze): add markdown generator for layout analysis"
```

---

## Task 6: 主入口脚本 (analyze_design.py)

**Files:**
- Create: `skills/analyze-lanhu-design/scripts/analyze_design.py`

- [ ] **Step 1: 创建主入口脚本**

```python
#!/usr/bin/env python3
"""
蓝湖设计数据分析工具

用法:
    python analyze_design.py <EXPORT_DIR> [--framework <framework>] [--design <name>]
"""
import argparse
import sys
from pathlib import Path

from layer_parser import LayerParser
from layout_analyzer import LayoutAnalyzer
from style_extractor import StyleExtractor
from markdown_generator import MarkdownGenerator


def find_project_root(start_path: Path = None) -> Path:
    """向上查找项目根目录"""
    if start_path is None:
        start_path = Path.cwd()

    current = start_path.resolve()
    while current != current.parent:
        if (current / '.claude').is_dir():
            return current
        current = current.parent
    return start_path


def find_slices(designs_dir: Path, design_name: str) -> list[tuple[str, str, int, int]]:
    """查找切图文件"""
    slices = []
    slices_dir = designs_dir.parent / 'slices' / design_name

    if not slices_dir.exists():
        return slices

    for img_file in slices_dir.glob('*'):
        if img_file.suffix.lower() in ['.png', '.svg', '.jpg', '.jpeg']:
            # 获取尺寸（简化处理，实际需要读取图片）
            slices.append((
                img_file.stem,
                f'slices/{design_name}/{img_file.name}',
                0, 0  # 尺寸后续可通过 PIL 获取
            ))

    return slices


def analyze_design(design_dir: Path, output_dir: Path, framework: str) -> bool:
    """分析单个设计"""
    sketch_path = design_dir / 'sketch.json'

    if not sketch_path.exists():
        print(f"  ⚠️ sketch.json not found in {design_dir}")
        return False

    print(f"  📊 Analyzing: {design_dir.name}")

    try:
        # 解析
        parser = LayerParser(sketch_path)
        root = parser.parse()
        meta = parser.get_meta()

        # 分析
        analyzer = LayoutAnalyzer(root)
        extractor = StyleExtractor(root)

        # 生成
        gen = MarkdownGenerator(framework)

        # 生成布局分析
        layout_md = gen.generate_layout_analysis(root, analyzer, extractor, meta)
        layout_file = output_dir / f'{design_dir.name}.md'
        layout_file.write_text(layout_md, encoding='utf-8')

        # 查找切图
        slices = find_slices(design_dir.parent, design_dir.name)

        return True

    except Exception as e:
        print(f"  ❌ Error analyzing {design_dir.name}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='分析蓝湖设计数据')
    parser.add_argument('export_dir', help='export-lanhu 导出目录')
    parser.add_argument('--framework', '-f', default='html',
                        choices=['html', 'vue', 'react', 'flutter', 'miniprogram', 'uniapp'],
                        help='目标框架 (默认: html)')
    parser.add_argument('--design', '-d', help='指定设计图名称')
    parser.add_argument('--output', '-o', help='自定义输出目录')

    args = parser.parse_args()

    export_dir = Path(args.export_dir)
    if not export_dir.exists():
        print(f"❌ Directory not found: {export_dir}")
        print("💡 请先运行 /export-lanhu 导出设计数据")
        sys.exit(1)

    # 确定输出目录
    output_dir = Path(args.output) if args.output else export_dir / 'analysis'
    output_dir.mkdir(parents=True, exist_ok=True)

    # 查找设计目录
    designs_dir = export_dir / 'designs'
    if not designs_dir.exists():
        print(f"❌ designs/ directory not found in {export_dir}")
        sys.exit(1)

    # 获取所有设计
    if args.design:
        design_dirs = [designs_dir / args.design]
        if not design_dirs[0].exists():
            print(f"❌ Design not found: {args.design}")
            sys.exit(1)
    else:
        design_dirs = [d for d in designs_dir.iterdir() if d.is_dir()]

    print(f"🎨 Analyzing {len(design_dirs)} designs...")
    print(f"📁 Framework: {args.framework}")
    print(f"📁 Output: {output_dir}")
    print()

    # 收集所有样式和切图
    all_colors = []
    all_fonts = []
    all_slices = []

    success_count = 0
    for design_dir in design_dirs:
        if analyze_design(design_dir, output_dir, args.framework):
            success_count += 1

    # 生成汇总文件
    print("\n📝 Generating summary files...")

    # 切图索引
    slices_md = MarkdownGenerator(args.framework).generate_slices_md(all_slices)
    (output_dir / 'slices.md').write_text(slices_md, encoding='utf-8')

    # 样式汇总
    styles_md = MarkdownGenerator(args.framework).generate_styles_md(all_colors[:20], all_fonts[:20])
    (output_dir / 'styles.md').write_text(styles_md, encoding='utf-8')

    # 组件详情（简化版）
    components_md = "# 组件详细说明\n\n请查看各设计图的布局分析文件。"
    (output_dir / 'components.md').write_text(components_md, encoding='utf-8')

    print(f"\n✅ Analysis completed!")
    print(f"   Designs: {success_count}/{len(design_dirs)}")
    print(f"   Output: {output_dir}")


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: 测试主入口**

```bash
cd E:/xen/code/claude/project/lanhu-mcp/skills/analyze-lanhu-design/scripts && python analyze_design.py ../../../docs/lanhu/pages/DesignProject-da907f83-2026032023 --design "便捷提货"
```

Expected: 生成 analysis/ 目录和 .md 文件

- [ ] **Step 3: Commit**

```bash
git add skills/analyze-lanhu-design/scripts/analyze_design.py
git commit -m "feat(analyze): add main entry script with CLI"
```

---

## Task 7: 技能文档 (SKILL.md)

**Files:**
- Create: `skills/analyze-lanhu-design/SKILL.md`

- [ ] **Step 1: 创建技能文档**

```markdown
---
name: analyze-lanhu-design
description: |
  解析蓝湖设计数据，生成 UI 布局描述文档。

  触发场景：分析设计、布局分析、UI 还原、设计转代码、切图索引、样式提取。

  当用户提到分析设计稿、生成布局文档、提取设计样式时，使用此 Skill。
compatibility:
  tools: [Bash, Read, Write]
  dependencies: []
---

## 使用方式

```bash
/analyze-lanhu-design <EXPORT_DIR> [--framework <framework>] [--design <name>]
```

## 参数

| 参数 | 说明 |
|------|------|
| `EXPORT_DIR` | export-lanhu 导出的目录路径（必填） |
| `--framework` | 目标框架: html/vue/react/flutter/miniprogram/uniapp (默认: html) |
| `--design` | 指定设计图名称（可选，默认处理所有） |
| `--output` | 自定义输出目录 |

## 前置条件

1. 已使用 /export-lanhu 导出设计数据
2. 导出目录包含 designs/ 和 slices/ 子目录

## 输出

```
{EXPORT_DIR}/analysis/
├── {设计名}.md        # 布局分析文档
├── components.md      # 组件详细说明
├── slices.md          # 切图索引
└── styles.md          # 样式汇总
```

## 布局分析文档内容

每个设计图的分析文档包含：

1. **概览** - 设备、尺寸、设计工具
2. **层级树形图** - 可视化组件嵌套关系
3. **区域示意图** - ASCII 布局图
4. **Flex 属性提示** - 推荐的 CSS Flex 属性
5. **间距对齐信息** - margin/padding 表格
6. **实现建议** - 布局方案和注意事项

## 执行步骤

1. 读取 designs/{设计名}/sketch.json
2. 解析图层结构
3. 分析布局模式
4. 提取样式变量
5. 生成 Markdown 文档

## 执行命令

```bash
cd skills/analyze-lanhu-design/scripts
python analyze_design.py "<EXPORT_DIR>"
```

## 示例

分析所有设计：

```bash
/analyze-lanhu-design docs/lanhu/pages/MyProject-2026032023
```

指定 Flutter 框架：

```bash
/analyze-lanhu-design docs/lanhu/pages/MyProject-2026032023 --framework flutter
```

分析单个设计：

```bash
/analyze-lanhu-design docs/lanhu/pages/MyProject-2026032023 --design "首页"
```

## 支持的框架

| 框架 | 标识 | 说明 |
|------|------|------|
| HTML | `html` | 标准 HTML + CSS |
| Vue | `vue` | Vue 组件 |
| React | `react` | React 组件 |
| Flutter | `flutter` | Flutter Widget |
| 小程序 | `miniprogram` | 微信小程序 |
| UniApp | `uniapp` | UniApp 组件 |
```

- [ ] **Step 2: Commit**

```bash
git add skills/analyze-lanhu-design/SKILL.md
git commit -m "docs(analyze): add SKILL.md documentation"
```

---

## Task 8: 参考文档

**Files:**
- Create: `skills/analyze-lanhu-design/references/layer-types.md`
- Create: `skills/analyze-lanhu-design/references/framework-mappings.md`

- [ ] **Step 1: 创建图层类型参考**

```markdown
# 图层类型参考

## 常见图层类型

| 类型 | 说明 | 处理方式 |
|------|------|----------|
| `shapeLayer` | 形状图层 | 提取填充、边框、圆角 |
| `textLayer` | 文本图层 | 提取文本内容和字体样式 |
| `group` | 图层组 | 递归处理子图层 |
| `symbolInstance` | 组件实例 | 作为普通图层处理 |
| `artboard` | 画板 | 根容器 |

## 样式属性

### fills (填充)
- `type`: color, gradient, image
- `color`: rgba 颜色值
- `opacity`: 透明度

### borders (边框)
- `color`: 边框颜色
- `width`: 边框宽度
- `position`: inside, outside, center

### shadows (阴影)
- `color`: 阴影颜色
- `blur`: 模糊半径
- `spread`: 扩展半径
- `x`, `y`: 偏移量

### radius (圆角)
- `topLeft`, `topRight`, `bottomLeft`, `bottomRight`
```

- [ ] **Step 2: 创建框架映射参考**

```markdown
# 框架映射参考

## 组件映射

| 通用 | HTML | Vue | React | Flutter | 小程序 | UniApp |
|------|------|-----|-------|---------|--------|--------|
| 容器 | `<div>` | `<div>` | `<div>` | `Container` | `<view>` | `<view>` |
| 文本 | `<span>` | `<span>` | `<span>` | `Text` | `<text>` | `<text>` |
| 图片 | `<img>` | `<img>` | `<img>` | `Image` | `<image>` | `<image>` |
| 按钮 | `<button>` | `<button>` | `<button>` | `TextButton` | `<button>` | `<button>` |

## Flex 映射

| CSS | Flutter | 说明 |
|-----|---------|------|
| `display: flex` | `Row/Column` | 弹性布局 |
| `flex-direction: row` | `Row` | 水平排列 |
| `flex-direction: column` | `Column` | 垂直排列 |
| `justify-content: center` | `mainAxisAlignment: MainAxisAlignment.center` | 主轴居中 |
| `align-items: center` | `crossAxisAlignment: CrossAxisAlignment.center` | 交叉轴居中 |
| `gap: 16px` | `SizedBox(height/width: 16)` | 间距 |

## 小程序特殊处理

小程序不支持 `gap` 属性，需要使用 `margin` 替代：

```css
/* 不支持 */
.container { gap: 16px; }

/* 替代方案 */
.container > view:not(:last-child) { margin-bottom: 16px; }
```
```

- [ ] **Step 3: Commit**

```bash
git add skills/analyze-lanhu-design/references/
git commit -m "docs(analyze): add reference documentation"
```

---

## Task 9: 集成测试

- [ ] **Step 1: 完整流程测试**

```bash
cd E:/xen/code/claude/project/lanhu-mcp/skills/analyze-lanhu-design/scripts
python analyze_design.py ../../../docs/lanhu/pages/DesignProject-da907f83-2026032023
```

Expected: 生成 analysis/ 目录，包含所有 .md 文件

- [ ] **Step 2: 验证输出文件**

```bash
ls ../../../docs/lanhu/pages/DesignProject-da907f83-2026032023/analysis/
```

Expected: 列出生成的 .md 文件

- [ ] **Step 3: 查看生成的布局分析**

```bash
cat ../../../docs/lanhu/pages/DesignProject-da907f83-2026032023/analysis/便捷提货.md
```

Expected: 显示完整的布局分析 Markdown

- [ ] **Step 4: Final Commit**

```bash
git add -A
git commit -m "feat(analyze): complete analyze-lanhu-design skill implementation"
```

---

## 成功标准

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

3. **多框架支持**
   - [ ] 支持 HTML 输出
   - [ ] 支持 Flutter 输出
   - [ ] 支持小程序/UniApp 输出
