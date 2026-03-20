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
