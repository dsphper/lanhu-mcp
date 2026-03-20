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
