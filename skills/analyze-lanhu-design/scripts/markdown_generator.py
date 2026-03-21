"""
Markdown 生成器 - 生成布局分析文档
"""
from typing import TYPE_CHECKING

from models import Layer, LayoutHint, Font

if TYPE_CHECKING:
    from layout_analyzer import LayoutAnalyzer
    from style_extractor import StyleExtractor


class MarkdownGenerator:
    """Markdown 文档生成器"""

    # 框架语法配置
    FRAMEWORK_SYNTAX = {
        'html': {
            'lang': 'css',
            'flex_prefix': '',
            'direction': {'row': 'flex-direction: row;', 'column': 'flex-direction: column;'},
            'justify': {
                'flex-start': 'justify-content: flex-start;',
                'center': 'justify-content: center;',
                'flex-end': 'justify-content: flex-end;',
                'space-between': 'justify-content: space-between;',
                'space-around': 'justify-content: space-around;',
            },
            'align': {
                'flex-start': 'align-items: flex-start;',
                'center': 'align-items: center;',
                'flex-end': 'align-items: flex-end;',
                'stretch': 'align-items: stretch;',
            },
        },
        'vue': {
            'lang': 'css',
            'flex_prefix': '',
            'direction': {'row': 'flex-direction: row;', 'column': 'flex-direction: column;'},
            'justify': {
                'flex-start': 'justify-content: flex-start;',
                'center': 'justify-content: center;',
                'flex-end': 'justify-content: flex-end;',
                'space-between': 'justify-content: space-between;',
                'space-around': 'justify-content: space-around;',
            },
            'align': {
                'flex-start': 'align-items: flex-start;',
                'center': 'align-items: center;',
                'flex-end': 'align-items: flex-end;',
                'stretch': 'align-items: stretch;',
            },
        },
        'react': {
            'lang': 'css',
            'flex_prefix': '',
            'direction': {'row': 'flex-direction: row;', 'column': 'flex-direction: column;'},
            'justify': {
                'flex-start': 'justify-content: flex-start;',
                'center': 'justify-content: center;',
                'flex-end': 'justify-content: flex-end;',
                'space-between': 'justify-content: space-between;',
                'space-around': 'justify-content: space-around;',
            },
            'align': {
                'flex-start': 'align-items: flex-start;',
                'center': 'align-items: center;',
                'flex-end': 'align-items: flex-end;',
                'stretch': 'align-items: stretch;',
            },
        },
        'flutter': {
            'lang': 'dart',
            'flex_prefix': '',
            'direction': {'row': 'Row(', 'column': 'Column('},
            'justify': {
                'flex-start': 'mainAxisAlignment: MainAxisAlignment.start,',
                'center': 'mainAxisAlignment: MainAxisAlignment.center,',
                'flex-end': 'mainAxisAlignment: MainAxisAlignment.end,',
                'space-between': 'mainAxisAlignment: MainAxisAlignment.spaceBetween,',
                'space-around': 'mainAxisAlignment: MainAxisAlignment.spaceAround,',
            },
            'align': {
                'flex-start': 'crossAxisAlignment: CrossAxisAlignment.start,',
                'center': 'crossAxisAlignment: CrossAxisAlignment.center,',
                'flex-end': 'crossAxisAlignment: CrossAxisAlignment.end,',
                'stretch': 'crossAxisAlignment: CrossAxisAlignment.stretch,',
            },
        },
        'miniprogram': {
            'lang': 'css',
            'flex_prefix': '',
            'direction': {'row': 'flex-direction: row;', 'column': 'flex-direction: column;'},
            'justify': {
                'flex-start': 'justify-content: flex-start;',
                'center': 'justify-content: center;',
                'flex-end': 'justify-content: flex-end;',
                'space-between': 'justify-content: space-between;',
                'space-around': 'justify-content: space-around;',
            },
            'align': {
                'flex-start': 'align-items: flex-start;',
                'center': 'align-items: center;',
                'flex-end': 'align-items: flex-end;',
                'stretch': 'align-items: stretch;',
            },
        },
        'uniapp': {
            'lang': 'css',
            'flex_prefix': '',
            'direction': {'row': 'flex-direction: row;', 'column': 'flex-direction: column;'},
            'justify': {
                'flex-start': 'justify-content: flex-start;',
                'center': 'justify-content: center;',
                'flex-end': 'justify-content: flex-end;',
                'space-between': 'justify-content: space-between;',
                'space-around': 'justify-content: space-around;',
            },
            'align': {
                'flex-start': 'align-items: flex-start;',
                'center': 'align-items: center;',
                'flex-end': 'align-items: flex-end;',
                'stretch': 'align-items: stretch;',
            },
        },
    }

    def __init__(self, framework: str = 'html'):
        """
        初始化生成器

        Args:
            framework: 目标框架 (html, vue, react, flutter, miniprogram, uniapp)
        """
        if framework not in self.FRAMEWORK_SYNTAX:
            raise ValueError(f"Unsupported framework: {framework}. "
                           f"Supported: {list(self.FRAMEWORK_SYNTAX.keys())}")
        self.framework = framework
        self.syntax = self.FRAMEWORK_SYNTAX[framework]

    def generate_layout_analysis(
        self,
        layer: Layer,
        analyzer: 'LayoutAnalyzer',
        extractor: 'StyleExtractor',
        meta: dict
    ) -> str:
        """
        生成布局分析文档

        Args:
            layer: 根图层
            analyzer: 布局分析器
            extractor: 样式提取器
            meta: 元信息

        Returns:
            Markdown 格式的分析文档
        """
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
        host = meta.get('host', {})
        host_name = host.get('name', 'Unknown')
        host_version = host.get('version', '')

        lines = [
            f"# {layer.name} - 布局分析",
            "",
            "| 属性 | 值 |",
            "|------|------|",
            f"| 设备 | {device} |",
            f"| 尺寸 | {layer.frame.width} x {layer.frame.height} |",
            f"| 设计工具 | {host_name} {host_version} |",
            f"| 图层深度 | {self._calc_depth(layer)} |",
            f"| 子图层数 | {self._count_children(layer)} |",
        ]
        return '\n'.join(lines)

    def _calc_depth(self, layer: Layer) -> int:
        """计算最大深度"""
        if not layer.children:
            return 1
        return 1 + max(self._calc_depth(child) for child in layer.children)

    def _count_children(self, layer: Layer) -> int:
        """递归计算所有子图层数量"""
        count = len(layer.children)
        for child in layer.children:
            count += self._count_children(child)
        return count

    def _generate_tree_diagram(self, layer: Layer) -> str:
        """生成 ASCII 树形图"""
        lines = ["## 图层结构", "", "```"]
        lines.extend(self._build_tree(layer, '', True))
        lines.append("```")
        return '\n'.join(lines)

    def _build_tree(self, layer: Layer, prefix: str, is_last: bool) -> list[str]:
        """递归构建树形图"""
        connector = '+-- ' if is_last else '+-- '
        type_icon = self._get_type_icon(layer.type)

        line = f"{prefix}{connector}{type_icon} {layer.name} ({layer.frame.width}x{layer.frame.height})"
        lines = [line]

        new_prefix = prefix + ('    ' if is_last else '|   ')

        for i, child in enumerate(layer.children):
            is_last_child = (i == len(layer.children) - 1)
            lines.extend(self._build_tree(child, new_prefix, is_last_child))

        return lines

    def _get_type_icon(self, layer_type: str) -> str:
        """获取图层类型图标"""
        icons = {
            'textLayer': '[T]',
            'shapeLayer': '[#]',
            'group': '[G]',
            'artboard': '[A]',
            'symbol': '[S]',
            'bitmap': '[I]',
        }
        return icons.get(layer_type, '[?]')

    def _generate_area_diagram(self, layer: Layer) -> str:
        """生成 ASCII 面积图"""
        lines = ["## 布局示意图", "", "```"]

        # 简单的 ASCII 盒子表示
        width = min(60, layer.frame.width // 10)
        height = min(20, layer.frame.height // 40)

        # 边框
        top_border = '+' + '-' * (width - 2) + '+'
        lines.append(top_border)

        # 内部区域
        for i in range(height - 2):
            if i == 0:
                lines.append('|' + ' ' * 5 + f'Width: {layer.frame.width}' + ' ' * (width - 20 - len(str(layer.frame.width))) + '|')
            elif i == height // 2 - 1:
                lines.append('|' + ' ' * 5 + f'Height: {layer.frame.height}' + ' ' * (width - 22 - len(str(layer.frame.height))) + '|')
            else:
                lines.append('|' + ' ' * (width - 2) + '|')

        lines.append(top_border)
        lines.append(f"```\n\n尺寸: {layer.frame.width}px x {layer.frame.height}px")

        return '\n'.join(lines)

    def _generate_flex_hints(self, layer: Layer, analyzer: 'LayoutAnalyzer') -> str:
        """生成 Flex 属性提示"""
        lines = ["## Flex 布局建议", ""]

        # 获取布局提示 (LayoutAnalyzer 在初始化时已分析完成)
        hints = analyzer.get_all_hints()

        if not hints:
            lines.append("无 Flex 布局建议。")
            return '\n'.join(lines)

        # 获取语法配置
        lang = self.syntax['lang']

        for layer_id, hint in hints.items():
            # 查找对应的图层名称
            layer_name = self._find_layer_name(layer, layer_id)
            if not layer_name:
                continue

            lines.append(f"### {layer_name}")
            lines.append("")
            lines.append(f"```{lang}")

            if self.framework == 'flutter':
                # Flutter 语法
                lines.append(f"// {hint.direction} 布局")
                lines.append(self.syntax['direction'][hint.direction])
                lines.append("  children: [")
                lines.append("    // ... 子组件")
                lines.append("  ],")
                lines.append(f"  {self.syntax['justify'].get(hint.justify, '')}")
                lines.append(f"  {self.syntax['align'].get(hint.align, '')}")
                lines.append(")")
            else:
                # CSS 语法
                lines.append(f".{layer_name.lower().replace(' ', '-')} {{")
                lines.append("  display: flex;")
                lines.append(f"  {self.syntax['direction'][hint.direction]}")
                lines.append(f"  {self.syntax['justify'].get(hint.justify, '')}")
                lines.append(f"  {self.syntax['align'].get(hint.align, '')}")
                if hint.gap > 0:
                    lines.append(f"  gap: {hint.gap}px;")
                lines.append("}")

            lines.append("```")
            lines.append("")

        return '\n'.join(lines)

    def _find_layer_name(self, layer: Layer, layer_id: str) -> str | None:
        """递归查找图层名称"""
        if layer.id == layer_id:
            return layer.name
        for child in layer.children:
            result = self._find_layer_name(child, layer_id)
            if result:
                return result
        return None

    def _generate_spacing_tables(self, layer: Layer, analyzer: 'LayoutAnalyzer') -> str:
        """生成间距表格"""
        lines = ["## 间距分析", ""]

        # 收集间距数据
        spacing_data = self._collect_spacing(layer, analyzer)

        if not spacing_data:
            lines.append("无间距数据。")
            return '\n'.join(lines)

        # 生成表格
        lines.append("| 图层名称 | Padding (T/R/B/L) | Margin (T/R/B/L) |")
        lines.append("|----------|-------------------|------------------|")

        for name, padding, margin in spacing_data:
            pad_str = f"{padding[0]}/{padding[1]}/{padding[2]}/{padding[3]}" if padding else "-"
            mar_str = f"{margin[0]}/{margin[1]}/{margin[2]}/{margin[3]}" if margin else "-"
            lines.append(f"| {name} | {pad_str} | {mar_str} |")

        return '\n'.join(lines)

    def _collect_spacing(
        self,
        layer: Layer,
        analyzer: 'LayoutAnalyzer'
    ) -> list[tuple[str, tuple | None, tuple | None]]:
        """收集间距数据"""
        result = []

        # 获取当前图层的布局提示 (包含 padding)
        hint = analyzer.get_hint(layer.id)
        if hint and hint.padding:
            # padding 是 (top, right, bottom, left)
            result.append((layer.name, hint.padding, None))

        # 递归处理子图层
        for child in layer.children:
            result.extend(self._collect_spacing(child, analyzer))

        return result

    def _generate_implementation_tips(self, layer: Layer, analyzer: 'LayoutAnalyzer') -> str:
        """生成实现建议"""
        lines = ["## 实现建议", ""]

        # 基于框架生成建议
        if self.framework == 'flutter':
            lines.extend(self._generate_flutter_tips(layer, analyzer))
        else:
            lines.extend(self._generate_css_tips(layer, analyzer))

        return '\n'.join(lines)

    def _generate_css_tips(self, layer: Layer, analyzer: 'LayoutAnalyzer') -> list[str]:
        """生成 CSS 实现建议"""
        lines = [
            "1. **使用 Flexbox 布局**: 大部分 UI 组件可以使用 Flexbox 实现",
            "2. **注意层级关系**: 使用 `z-index` 管理图层叠加顺序",
            "3. **响应式设计**: 考虑使用相对单位 (rem, vw, vh) 适配不同屏幕",
            "4. **圆角处理**: 注意 `border-radius` 的统一性",
            "",
            "### 代码示例",
            "",
            "```css",
            f".{layer.name.lower().replace(' ', '-')} {{",
            f"  width: {layer.frame.width}px;",
            f"  height: {layer.frame.height}px;",
            "  position: relative;",
            "  box-sizing: border-box;",
            "}",
            "```",
        ]
        return lines

    def _generate_flutter_tips(self, layer: Layer, analyzer: 'LayoutAnalyzer') -> list[str]:
        """生成 Flutter 实现建议"""
        lines = [
            "1. **使用 Row/Column**: 布局主要使用 Row 和 Column 组件",
            "2. **间距控制**: 使用 Padding 和 Margin 控制组件间距",
            "3. **层级管理**: 使用 Stack 和 Positioned 处理叠加布局",
            "4. **圆角处理**: 使用 Container 的 decoration 属性",
            "",
            "### 代码示例",
            "",
            "```dart",
            f"Widget build{layer.name.replace(' ', '')}() {{",
            "  return Container(",
            f"    width: {layer.frame.width},",
            f"    height: {layer.frame.height},",
            "    child: Stack(",
            "      children: [",
            "        // 添加子组件",
            "      ],",
            "    ),",
            "  );",
            "}",
            "```",
        ]
        return lines

    def generate_slices_md(self, slices: list[tuple[str, str, int, int]]) -> str:
        """
        生成切片索引 Markdown

        Args:
            slices: 切片列表 [(name, path, width, height), ...]

        Returns:
            Markdown 格式的切片索引
        """
        lines = ["## 切图资源", ""]

        if not slices:
            lines.append("无切图资源。")
            return '\n'.join(lines)

        lines.append("| 名称 | 路径 | 尺寸 |")
        lines.append("|------|------|------|")

        for name, path, width, height in slices:
            lines.append(f"| {name} | `{path}` | {width}x{height} |")

        lines.append("")
        lines.append(f"**总计**: {len(slices)} 个切图")

        return '\n'.join(lines)

    def generate_styles_md(
        self,
        colors: list[tuple[str, str]],
        fonts: list[tuple[str, Font]]
    ) -> str:
        """
        生成样式摘要 Markdown

        Args:
            colors: 颜色列表 [(name, hex_value), ...]
            fonts: 字体列表 [(name, Font), ...]

        Returns:
            Markdown 格式的样式摘要
        """
        lines = ["## 样式摘要", ""]

        # 颜色部分
        lines.append("### 颜色")
        lines.append("")
        lines.append("| 名称 | 色值 | 预览 |")
        lines.append("|------|------|------|")

        for name, hex_value in colors:
            lines.append(f"| {name} | `{hex_value}` | ![{hex_value}](data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' width='20' height='20'><rect fill='{hex_value}' width='20' height='20'/></svg>) |")

        lines.append("")

        # 字体部分
        lines.append("### 字体")
        lines.append("")
        lines.append("| 名称 | 字体 | 大小 | 行高 |")
        lines.append("|------|------|------|------|")

        for name, font in fonts:
            lines.append(f"| {name} | {font.name} | {font.size}px | {font.line_height}px |")

        return '\n'.join(lines)
