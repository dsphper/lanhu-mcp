"""
sketch.json 解析器
"""
import json
from pathlib import Path
from typing import Any

from models import (
    Layer, Frame, Style, Fill, Border, Shadow, Color,
    Radius, TextContent, Font, ImageRef
)


class ParseError(Exception):
    """解析错误"""
    pass


class LayerParser:
    """解析 sketch.json 为 Layer 树"""

    def __init__(self, sketch_path: str | Path):
        self.sketch_path = Path(sketch_path)
        self.data = self._load_json()

    def _load_json(self) -> dict:
        # 验证文件存在
        if not self.sketch_path.exists():
            raise ParseError(f"sketch.json not found: {self.sketch_path}")

        # 加载并解析 JSON
        try:
            with open(self.sketch_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ParseError(
                f"Invalid JSON in {self.sketch_path}: {e.msg} at line {e.lineno}"
            ) from e

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
            r=int(data.get('r', 0)),
            g=int(data.get('g', 0)),
            b=int(data.get('b', 0)),
            a=float(data.get('a', 1.0)),
            value=data.get('value', '')
        )

    def _parse_text(self, data: dict) -> TextContent:
        style = data.get('style', {}) or {}
        font_data = style.get('font', {}) or {}

        # 安全获取嵌套值
        line_height_data = font_data.get('lineHeight') or {}
        letter_spacing_data = font_data.get('letterSpacing') or {}

        font = Font(
            name=font_data.get('name', 'sans-serif'),
            size=font_data.get('size', 14),
            weight=font_data.get('type', 'Regular'),
            line_height=font_data.get('lineSpacing', line_height_data.get('value', 20)),
            letter_spacing=letter_spacing_data.get('value', 0),
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
