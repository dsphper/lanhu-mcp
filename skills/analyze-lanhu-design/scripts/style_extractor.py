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
