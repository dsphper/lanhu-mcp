# Export Lanhu 增强功能 实现计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 export-lanhu skill 添加四项增强功能：设计图选择交互、按关键词分组保存、平台适配、切图格式和比例支持

**Architecture:** 模块化设计，将功能拆分为独立模块（选择解析器、平台配置、格式转换器），主脚本通过参数组合调用各模块

**Tech Stack:** Python 3.10+, argparse, httpx, asyncio, Pillow (图片格式转换)

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `skills/export-lanhu/scripts/selection_parser.py` | 创建 | 选择表达式解析 |
| `skills/export-lanhu/scripts/platform_config.py` | 创建 | 平台配置（倍率、命名规则、目录结构） |
| `skills/export-lanhu/scripts/format_converter.py` | 创建 | 图片格式转换（PNG→WebP/JPG） |
| `skills/export-lanhu/scripts/export_lanhu.py` | 修改 | 主脚本，集成所有模块，添加新参数 |
| `skills/export-lanhu/SKILL.md` | 修改 | 更新交互流程，添加平台/格式参数说明 |

---

## Task 1: 创建选择表达式解析器

**Files:**
- Create: `skills/export-lanhu/scripts/selection_parser.py`
- Test: `skills/export-lanhu/scripts/test_selection_parser.py`

- [ ] **Step 1: 编写选择解析器测试**

```python
# test_selection_parser.py
import pytest
from selection_parser import parse_selection, SelectionParseError


class TestParseSelection:
    """选择表达式解析测试"""

    def test_single_number(self):
        """单选：1 → [0]"""
        assert parse_selection("1", 10) == [0]

    def test_multiple_numbers(self):
        """多选：1,3,5 → [0, 2, 4]"""
        assert parse_selection("1,3,5", 10) == [0, 2, 4]

    def test_range(self):
        """范围：1-5 → [0, 1, 2, 3, 4]"""
        assert parse_selection("1-5", 10) == [0, 1, 2, 3, 4]

    def test_range_and_numbers(self):
        """范围+单选：1-3,5,7 → [0, 1, 2, 4, 6]"""
        assert parse_selection("1-3,5,7", 10) == [0, 1, 2, 4, 6]

    def test_exclude(self):
        """排除：1-5 -2,4 → [0, 2]"""
        assert parse_selection("1-5 -2,4", 10) == [0, 2]

    def test_select_all(self):
        """全选：* → [0..9]"""
        assert parse_selection("*", 10) == list(range(10))

    def test_exclude_all(self):
        """全选后排除：^2,4 → [0, 1, 3, 5, 6, 7, 8, 9]"""
        assert parse_selection("^2,4", 10) == [0, 1, 3, 5, 6, 7, 8, 9]

    def test_exclude_range(self):
        """排除范围：1-10 -3-5 → [0, 1, 5, 6, 7, 8, 9]"""
        assert parse_selection("1-10 -3-5", 10) == [0, 1, 5, 6, 7, 8, 9]

    def test_out_of_range(self):
        """超出范围抛出错误"""
        with pytest.raises(SelectionParseError):
            parse_selection("1-20", 10)

    def test_invalid_syntax(self):
        """无效语法抛出错误"""
        with pytest.raises(SelectionParseError):
            parse_selection("1--5", 10)

    def test_empty_string(self):
        """空字符串返回全选"""
        assert parse_selection("", 10) == list(range(10))

    def test_whitespace_handling(self):
        """空格处理"""
        assert parse_selection("  1 , 3 , 5  ", 10) == [0, 2, 4]
        assert parse_selection("1 - 5  -  2 , 4", 10) == [0, 2]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd skills/export-lanhu/scripts
python -m pytest test_selection_parser.py -v
```

Expected: FAIL (module not found)

- [ ] **Step 3: 实现选择解析器**

```python
# selection_parser.py
"""
选择表达式解析器

语法:
    1,3,5      - 选择第 1、3、5 个
    1-5        - 选择第 1 到 5 个
    1-5,8,10   - 范围和单选组合
    1-5 -2,4   - 范围选择后排除 2 和 4
    *          - 全选
    ^2,4       - 全选后排除 2 和 4
"""
import re
from typing import List


class SelectionParseError(Exception):
    """选择表达式解析错误"""
    pass


def _parse_numbers(expr: str, total: int) -> set:
    """
    解析数字表达式（不含排除）

    Args:
        expr: 表达式如 "1-5,8,10"
        total: 总数量

    Returns:
        选中的索引集合（0-based）
    """
    selected = set()

    if not expr.strip():
        return selected

    parts = expr.split(',')
    for part in parts:
        part = part.strip()
        if not part:
            continue

        if '-' in part:
            # 范围表达式
            match = re.match(r'^(\d+)\s*-\s*(\d+)$', part)
            if not match:
                raise SelectionParseError(f"Invalid range: {part}")
            start, end = int(match.group(1)), int(match.group(2))
            if start > end:
                raise SelectionParseError(f"Invalid range: {start} > {end}")
            if end > total:
                raise SelectionParseError(f"Index {end} out of range (max: {total})")
            selected.update(range(start - 1, end))  # 转为 0-based
        else:
            # 单个数字
            try:
                num = int(part)
            except ValueError:
                raise SelectionParseError(f"Invalid number: {part}")
            if num < 1 or num > total:
                raise SelectionParseError(f"Index {num} out of range (1-{total})")
            selected.add(num - 1)  # 转为 0-based

    return selected


def parse_selection(expression: str, total_count: int) -> List[int]:
    """
    解析选择表达式

    Args:
        expression: 选择表达式
        total_count: 总数量

    Returns:
        选中的索引列表（0-based，已排序）

    Raises:
        SelectionParseError: 表达式无效

    Examples:
        "1,3,5" → [0, 2, 4]
        "1-5" → [0, 1, 2, 3, 4]
        "1-5 -2,4" → [0, 2]
        "*" → [0, 1, ..., total_count-1]
        "^2,4" → 全选后排除
    """
    if total_count <= 0:
        return []

    expression = expression.strip()

    # 空字符串或 * 表示全选
    if not expression or expression == '*':
        return list(range(total_count))

    # 检查排除模式（以 ^ 开头）
    if expression.startswith('^'):
        exclude_expr = expression[1:].strip()
        all_indices = set(range(total_count))
        exclude_set = _parse_numbers(exclude_expr, total_count)
        result = all_indices - exclude_set
        return sorted(result)

    # 检查是否有排除部分（空格后的 -）
    # 使用正则匹配 "select -exclude" 模式
    match = re.match(r'^(.+?)\s+-(.+)$', expression)
    if match:
        select_expr = match.group(1).strip()
        exclude_expr = match.group(2).strip()
        select_set = _parse_numbers(select_expr, total_count)
        exclude_set = _parse_numbers(exclude_expr, total_count)
        result = select_set - exclude_set
        return sorted(result)

    # 纯选择模式
    select_set = _parse_numbers(expression, total_count)
    return sorted(select_set)
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd skills/export-lanhu/scripts
python -m pytest test_selection_parser.py -v
```

Expected: All tests pass

- [ ] **Step 5: 提交**

```bash
git add skills/export-lanhu/scripts/selection_parser.py
git add skills/export-lanhu/scripts/test_selection_parser.py
git commit -m "feat(export): add selection expression parser"
```

---

## Task 2: 创建平台配置模块

**Files:**
- Create: `skills/export-lanhu/scripts/platform_config.py`
- Test: `skills/export-lanhu/scripts/test_platform_config.py`

- [ ] **Step 1: 编写平台配置测试**

```python
# test_platform_config.py
import pytest
from pathlib import Path
from platform_config import (
    Platform,
    PlatformConfig,
    get_platform_config,
    get_slice_filename,
    get_slice_output_path
)


class TestPlatformConfig:
    """平台配置测试"""

    def test_ios_config(self):
        """iOS 配置"""
        config = get_platform_config('ios')
        assert config.name == 'ios'
        assert '2x' in config.scales
        assert '3x' in config.scales
        assert config.default_scale == '3x'

    def test_android_config(self):
        """Android 配置"""
        config = get_platform_config('android')
        assert config.name == 'android'
        assert 'xxxhdpi' in config.scales
        assert config.default_scale == 'xxxhdpi'

    def test_web_config(self):
        """Web 配置"""
        config = get_platform_config('web')
        assert config.name == 'web'
        assert '1x' in config.scales
        assert '2x' in config.scales
        assert config.default_scale == '2x'

    def test_invalid_platform(self):
        """无效平台抛出错误"""
        with pytest.raises(ValueError):
            get_platform_config('invalid')

    def test_ios_filename(self):
        """iOS 文件命名"""
        assert get_slice_filename('icon', 'ios', '3x', 'png') == 'icon@3x.png'
        assert get_slice_filename('icon', 'ios', '2x', 'webp') == 'icon@2x.webp'

    def test_android_filename(self):
        """Android 文件命名（倍率体现在目录）"""
        assert get_slice_filename('icon', 'android', 'xxxhdpi', 'png') == 'icon.png'
        assert get_slice_filename('icon', 'android', 'hdpi', 'webp') == 'icon.webp'

    def test_web_filename(self):
        """Web 文件命名"""
        assert get_slice_filename('icon', 'web', '1x', 'png') == 'icon.png'
        assert get_slice_filename('icon', 'web', '2x', 'png') == 'icon@2x.png'

    def test_ios_output_path(self):
        """iOS 输出路径"""
        base = Path('/output')
        path = get_slice_output_path(base, 'ios', '登录', '设计A', '3x', 'icon@3x.png')
        expected = Path('/output/iOS/登录/设计A/icon@3x.png')
        assert path == expected

    def test_android_output_path(self):
        """Android 输出路径"""
        base = Path('/output')
        path = get_slice_output_path(base, 'android', '登录', '设计A', 'xxxhdpi', 'icon.png')
        expected = Path('/output/Android/drawable-xxxhdpi/登录/设计A/icon.png')
        assert path == expected

    def test_web_output_path(self):
        """Web 输出路径"""
        base = Path('/output')
        path = get_slice_output_path(base, 'web', '登录', '设计A', '2x', 'icon@2x.png')
        expected = Path('/output/Web/登录/设计A/icon@2x.png')
        assert path == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd skills/export-lanhu/scripts
python -m pytest test_platform_config.py -v
```

Expected: FAIL (module not found)

- [ ] **Step 3: 实现平台配置**

```python
# platform_config.py
"""
平台配置模块

支持 iOS、Android、Web 三种平台的切图配置
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Literal


PlatformName = Literal['ios', 'android', 'web']


@dataclass
class PlatformConfig:
    """平台配置"""
    name: str
    display_name: str
    scales: Dict[str, float]  # scale_name -> multiplier
    default_scale: str
    size_unit: str  # pt, dp, px


# 平台配置表
PLATFORM_CONFIGS: Dict[str, PlatformConfig] = {
    'ios': PlatformConfig(
        name='ios',
        display_name='iOS',
        scales={
            '1x': 1.0,
            '2x': 2.0,
            '3x': 3.0,
        },
        default_scale='3x',
        size_unit='pt'
    ),
    'android': PlatformConfig(
        name='android',
        display_name='Android',
        scales={
            'mdpi': 1.0,
            'hdpi': 1.5,
            'xhdpi': 2.0,
            'xxhdpi': 3.0,
            'xxxhdpi': 4.0,
        },
        default_scale='xxxhdpi',
        size_unit='dp'
    ),
    'web': PlatformConfig(
        name='web',
        display_name='Web',
        scales={
            '1x': 1.0,
            '2x': 2.0,
        },
        default_scale='2x',
        size_unit='px'
    )
}


def get_platform_config(platform: str) -> PlatformConfig:
    """
    获取平台配置

    Args:
        platform: 平台名称 (ios/android/web)

    Returns:
        平台配置

    Raises:
        ValueError: 无效的平台名称
    """
    platform = platform.lower()
    if platform not in PLATFORM_CONFIGS:
        raise ValueError(f"Invalid platform: {platform}. Must be one of: ios, android, web")
    return PLATFORM_CONFIGS[platform]


def get_slice_filename(
    name: str,
    platform: str,
    scale: str,
    format: str
) -> str:
    """
    生成切图文件名

    Args:
        name: 切图名称（不含扩展名）
        platform: 平台 (ios/android/web)
        scale: 倍率
        format: 格式 (png/webp/svg/jpg)

    Returns:
        文件名
    """
    if platform == 'ios':
        # iOS: icon@3x.png
        return f"{name}@{scale}.{format}"
    elif platform == 'android':
        # Android: icon.png (倍率体现在目录名)
        return f"{name}.{format}"
    else:  # web
        # Web: icon.png 或 icon@2x.png
        if scale == '1x':
            return f"{name}.{format}"
        return f"{name}@{scale}.{format}"


def get_slice_output_path(
    base_dir: Path,
    platform: str,
    keyword: str,
    design_name: str,
    scale: str,
    filename: str
) -> Path:
    """
    生成切图输出路径

    Args:
        base_dir: slices 基础目录
        platform: 平台 (ios/android/web)
        keyword: 关键词分组
        design_name: 设计图名称
        scale: 倍率
        filename: 文件名

    Returns:
        完整输出路径

    Examples:
        iOS:    slices/iOS/登录/设计A/icon@3x.png
        Android: slices/Android/drawable-xxxhdpi/登录/设计A/icon.png
        Web:    slices/Web/登录/设计A/icon@2x.png
    """
    if platform == 'ios':
        return base_dir / 'iOS' / keyword / design_name / filename
    elif platform == 'android':
        scale_dir = f"drawable-{scale}"
        return base_dir / 'Android' / scale_dir / keyword / design_name / filename
    else:  # web
        return base_dir / 'Web' / keyword / design_name / filename


def get_all_scales(platform: str) -> List[str]:
    """
    获取平台的所有倍率

    Args:
        platform: 平台名称

    Returns:
        倍率名称列表
    """
    config = get_platform_config(platform)
    return list(config.scales.keys())
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd skills/export-lanhu/scripts
python -m pytest test_platform_config.py -v
```

Expected: All tests pass

- [ ] **Step 5: 提交**

```bash
git add skills/export-lanhu/scripts/platform_config.py
git add skills/export-lanhu/scripts/test_platform_config.py
git commit -m "feat(export): add platform configuration module"
```

---

## Task 3: 创建格式转换模块

**Files:**
- Create: `skills/export-lanhu/scripts/format_converter.py`
- Test: `skills/export-lanhu/scripts/test_format_converter.py`

- [ ] **Step 1: 编写格式转换测试**

```python
# test_format_converter.py
import pytest
from io import BytesIO
from PIL import Image

from format_converter import convert_format, resize_to_scale


class TestFormatConverter:
    """格式转换测试"""

    @pytest.fixture
    def sample_png(self):
        """创建测试用 PNG 图片"""
        img = Image.new('RGBA', (100, 100), color=(255, 0, 0, 128))
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()

    def test_png_to_webp(self, sample_png):
        """PNG → WebP 转换"""
        result = convert_format(sample_png, 'webp')
        img = Image.open(BytesIO(result))
        assert img.format == 'WEBP'
        assert img.size == (100, 100)

    def test_png_to_jpg(self, sample_png):
        """PNG → JPG 转换（透明通道转白）"""
        result = convert_format(sample_png, 'jpg')
        img = Image.open(BytesIO(result))
        assert img.format == 'JPEG'
        assert img.mode == 'RGB'  # JPEG 不支持透明

    def test_png_passthrough(self, sample_png):
        """PNG 直接返回"""
        result = convert_format(sample_png, 'png')
        assert result == sample_png

    def test_webp_quality(self, sample_png):
        """WebP 质量参数"""
        result_low = convert_format(sample_png, 'webp', quality=50)
        result_high = convert_format(sample_png, 'webp', quality=100)
        # 低质量文件更小
        assert len(result_low) < len(result_high)

    def test_resize_to_scale(self, sample_png):
        """缩放到指定倍率"""
        img = Image.open(BytesIO(sample_png))

        # 缩小到 0.5 倍
        resized = resize_to_scale(img, 1.0, 2.0)
        assert resized.size == (50, 50)

        # 不缩放
        same = resize_to_scale(img, 2.0, 2.0)
        assert same.size == (100, 100)

    def test_invalid_format(self, sample_png):
        """无效格式返回原图"""
        result = convert_format(sample_png, 'invalid')
        assert result == sample_png


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd skills/export-lanhu/scripts
python -m pytest test_format_converter.py -v
```

Expected: FAIL (module not found)

- [ ] **Step 3: 实现格式转换器**

```python
# format_converter.py
"""
图片格式转换模块

支持 PNG、WebP、JPG 格式互转
"""
from PIL import Image
from io import BytesIO
from typing import Tuple


def convert_format(
    png_data: bytes,
    target_format: str,
    quality: int = 85
) -> bytes:
    """
    转换图片格式

    Args:
        png_data: PNG 格式的图片数据
        target_format: 目标格式 (png/webp/jpg)
        quality: 压缩质量 (1-100)，用于 WebP 和 JPG

    Returns:
        转换后的图片数据（PNG 格式请求时返回原数据）
    """
    target_format = target_format.lower()

    # PNG 直接返回
    if target_format == 'png':
        return png_data

    img = Image.open(BytesIO(png_data))

    if target_format == 'webp':
        output = BytesIO()
        # WebP 支持透明通道
        img.save(output, format='WEBP', quality=quality)
        return output.getvalue()

    elif target_format == 'jpg' or target_format == 'jpeg':
        # JPEG 不支持透明通道，需要转换
        if img.mode in ('RGBA', 'P'):
            # 创建白色背景
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[3])  # 使用 alpha 通道作为 mask
            img = background
        output = BytesIO()
        img.save(output, format='JPEG', quality=quality)
        return output.getvalue()

    # 未知格式，返回原图
    return png_data


def resize_to_scale(
    img: Image.Image,
    target_scale: float,
    max_scale: float
) -> Image.Image:
    """
    将最大倍率图片缩小到目标倍率

    Args:
        img: 原始图片（最大倍率）
        target_scale: 目标倍率 (如 1.0, 2.0, 3.0)
        max_scale: 最大倍率 (如 3.0 或 4.0)

    Returns:
        缩放后的图片
    """
    if target_scale >= max_scale:
        return img

    ratio = target_scale / max_scale
    new_size = (int(img.width * ratio), int(img.height * ratio))
    return img.resize(new_size, Image.Resampling.LANCZOS)


def get_available_formats() -> Tuple[str, ...]:
    """
    获取支持的格式列表

    Returns:
        支持的格式元组
    """
    return ('png', 'webp', 'jpg', 'svg')
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd skills/export-lanhu/scripts
python -m pytest test_format_converter.py -v
```

Expected: All tests pass

- [ ] **Step 5: 提交**

```bash
git add skills/export-lanhu/scripts/format_converter.py
git add skills/export-lanhu/scripts/test_format_converter.py
git commit -m "feat(export): add format converter module"
```

---

## Task 4: 添加分组逻辑函数

**Files:**
- Modify: `skills/export-lanhu/scripts/export_lanhu.py` (在 filter_designs_by_keywords 函数后添加)

- [ ] **Step 1: 添加分组逻辑函数**

在 `filter_designs_by_keywords` 函数后添加：

```python
def get_design_group(design_name: str, keywords: list) -> str:
    """
    根据设计名和关键词确定分组

    Args:
        design_name: 设计图名称
        keywords: 过滤关键词列表

    Returns:
        分组名称（空字符串表示不分组）
    """
    # 无关键词时，不分组
    if not keywords:
        return ""

    for keyword in keywords:
        if keyword.lower() in design_name.lower():
            return keyword
    return "_其他"


def get_design_output_path(base_dir: Path, design_name: str, keywords: list) -> Path:
    """
    获取设计输出路径

    Args:
        base_dir: designs 基础目录
        design_name: 设计图名称（已清理）
        keywords: 过滤关键词列表

    Returns:
        设计输出路径
    """
    group = get_design_group(design_name, keywords)

    if group:
        # 有关键词分组
        return base_dir / group / design_name
    else:
        # 无关键词，不分组
        return base_dir / design_name
```

- [ ] **Step 2: 提交**

```bash
git add skills/export-lanhu/scripts/export_lanhu.py
git commit -m "feat(export): add grouping logic for designs"
```

---

## Task 5: 添加错误处理类

**Files:**
- Modify: `skills/export-lanhu/scripts/export_lanhu.py` (在 import 部分后添加)

- [ ] **Step 1: 添加错误处理类和重试逻辑**

在 import 部分后添加：

```python
from dataclasses import dataclass, field


# ============ 错误处理 ============

class LanhuExportError(Exception):
    """导出错误基类"""
    pass


class AuthenticationError(LanhuExportError):
    """认证失败"""
    pass


class NetworkError(LanhuExportError):
    """网络错误（可重试）"""
    pass


class ResourceNotFoundError(LanhuExportError):
    """资源不存在（跳过）"""
    pass


@dataclass
class ExportResult:
    """导出结果统计"""
    success: bool
    output_dir: Path
    designs_total: int = 0
    designs_success: int = 0
    designs_failed: int = 0
    slices_total: int = 0
    slices_success: int = 0
    slices_failed: int = 0
    errors: list = field(default_factory=list)

    def add_error(self, error: str):
        """添加错误记录"""
        self.errors.append(error)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'success': self.success,
            'output_dir': str(self.output_dir),
            'designs': {
                'total': self.designs_total,
                'success': self.designs_success,
                'failed': self.designs_failed,
            },
            'slices': {
                'total': self.slices_total,
                'success': self.slices_success,
                'failed': self.slices_failed,
            },
            'errors': self.errors,
        }
```

- [ ] **Step 2: 修改 download_file 函数添加重试逻辑**

将 `download_file` 函数改为：

```python
async def download_file(
    client: httpx.AsyncClient,
    url: str,
    output_path: Path,
    max_retries: int = 3,
    initial_delay: float = 1.0
) -> bool:
    """
    下载文件（带重试）

    Args:
        client: HTTP 客户端
        url: 文件 URL
        output_path: 输出路径
        max_retries: 最大重试次数
        initial_delay: 初始延迟秒数

    Returns:
        是否成功
    """
    delay = initial_delay
    last_error = None

    for attempt in range(max_retries):
        try:
            response = await client.get(url)
            response.raise_for_status()

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(response.content)
            return True
        except httpx.TimeoutException as e:
            last_error = e
            if attempt < max_retries - 1:
                print(f"  ⚠️ Timeout, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(delay)
                delay *= 2  # 指数退避
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Authentication failed. Please check your Cookie.")
            if e.response.status_code == 404:
                print(f"  ⚠️ Resource not found: {url}")
                return False
            last_error = e
            if attempt < max_retries - 1:
                print(f"  ⚠️ HTTP error, retrying in {delay}s")
                await asyncio.sleep(delay)
                delay *= 2
        except Exception as e:
            print(f"  ⚠️ Failed to download {url}: {e}")
            return False

    print(f"  ⚠️ Failed after {max_retries} retries: {last_error}")
    return False
```

- [ ] **Step 3: 提交**

```bash
git add skills/export-lanhu/scripts/export_lanhu.py
git commit -m "feat(export): add error handling classes and retry logic"
```

---

## Task 6: 添加新命令行参数

**Files:**
- Modify: `skills/export-lanhu/scripts/export_lanhu.py` (main 函数)

- [ ] **Step 1: 在 main 函数中添加新参数**

在 `--ids` 参数后添加：

```python
    parser.add_argument('--ids', type=str,
                        help='指定设计 ID 导出（逗号分隔，精确控制）')

    # 新增增强功能参数
    parser.add_argument('--select', type=str,
                        help='选择表达式（如 1-3,5 或 1-10 -2,4），跳过交互')
    parser.add_argument('--platform', type=str, default='ios',
                        choices=['ios', 'android', 'web'],
                        help='目标平台 (默认: ios)')
    parser.add_argument('--scales', type=str, default='all',
                        help='切图比例 (all 或 2x,3x / mdpi,hdpi 等)')
    parser.add_argument('--formats', type=str, default='png',
                        help='切图格式 (png,webp,svg)，逗号分隔')
```

- [ ] **Step 2: 在 args 解析后添加新参数处理**

在 `design_ids` 解析后添加：

```python
    # 解析 --ids
    design_ids = None
    if args.ids:
        design_ids = [id.strip() for id in args.ids.split(',') if id.strip()]

    # 解析 --scales
    target_scales = None  # None 表示使用默认
    if args.scales and args.scales.lower() != 'all':
        target_scales = [s.strip() for s in args.scales.split(',') if s.strip()]

    # 解析 --formats
    target_formats = [f.strip().lower() for f in args.formats.split(',') if f.strip()]
    if not target_formats:
        target_formats = ['png']
```

- [ ] **Step 3: 提交**

```bash
git add skills/export-lanhu/scripts/export_lanhu.py
git commit -m "feat(export): add new command line arguments for enhanced features"
```

---

## Task 7: 修改 export_lanhu 函数支持新功能

**Files:**
- Modify: `skills/export-lanhu/scripts/export_lanhu.py`

- [ ] **Step 1: 修改 export_lanhu 函数签名**

将函数签名改为：

```python
async def export_lanhu(
    url: str,
    output_base_dir: Path,
    cookie: str,
    include_slices: bool = True,
    include_preview: bool = True,
    timeout: int = 30,
    keywords: list = None,
    design_ids: list = None,
    # 新增参数
    selection: list = None,  # 选择后的索引列表
    platform: str = 'ios',
    target_scales: list = None,  # None 表示使用默认
    target_formats: list = None  # None 表示 ['png']
) -> dict:
```

- [ ] **Step 2: 添加导入**

在文件顶部 import 部分添加：

```python
from selection_parser import parse_selection, SelectionParseError
from platform_config import (
    get_platform_config,
    get_slice_filename,
    get_slice_output_path,
    get_all_scales
)
from format_converter import convert_format, resize_to_scale
```

- [ ] **Step 3: 修改设计过滤逻辑支持选择表达式**

在 `# 4.5 根据条件过滤设计` 部分改为：

```python
        # 4.5 根据条件过滤设计
        if design_ids:
            # 按 ID 精确过滤
            designs = [d for d in designs if d['id'] in design_ids]
            print(f"🔍 Filtered by IDs: {len(designs)} designs")
        elif keywords:
            # 按关键词过滤
            matched, unmatched = filter_designs_by_keywords(designs, keywords)
            if selection is not None:
                # 在匹配结果中按索引选择
                designs = [matched[i] for i in selection if i < len(matched)]
                print(f"🔍 Selected {len(designs)} from {len(matched)} matched designs")
            else:
                designs = matched
                print(f"🔍 Filtered by keywords: {len(designs)} designs")
        elif selection is not None:
            # 无关键词，在全量设计中按索引选择
            designs = [designs[i] for i in selection if i < len(designs)]
            print(f"🔍 Selected {len(designs)} designs by index")
```

- [ ] **Step 4: 修改设计下载逻辑支持分组**

将设计下载部分改为：

```python
        # 5. 下载设计数据（按关键词分组）
        print(f"📦 Downloading {len(designs)} designs...")
        designs_dir = output_dir / 'designs'
        designs_dir.mkdir(exist_ok=True)

        design_results = []
        for i, design in enumerate(designs, 1):
            design_name = sanitize_filename(design.get('name', 'unknown'))
            design['team_id'] = team_id
            design['project_id'] = project_id

            # 获取分组路径
            design_output = get_design_output_path(designs_dir, design_name, keywords)
            design_output.mkdir(parents=True, exist_ok=True)

            print(f"  [{i}/{len(designs)}] {design.get('name', 'unknown')}")
            result = await download_design_data(
                api, design, design_output.parent, design_output.name, include_preview
            )
            design_results.append(result)
```

- [ ] **Step 5: 提交**

```bash
git add skills/export-lanhu/scripts/export_lanhu.py
git commit -m "feat(export): integrate selection and grouping into export_lanhu"
```

---

## Task 8: 修改切图下载逻辑支持平台和格式

**Files:**
- Modify: `skills/export-lanhu/scripts/export_lanhu.py`

- [ ] **Step 1: 重写切图下载部分**

将 `# 6. 下载切图` 部分改为：

```python
        # 6. 下载切图（按平台、关键词分组，支持多格式）
        slice_count = 0
        if include_slices:
            print("🖼️ Downloading slices...")
            platform_config = get_platform_config(platform)

            # 确定要导出的倍率
            if target_scales:
                scales_to_export = target_scales
            else:
                scales_to_export = [platform_config.default_scale]

            formats_to_export = target_formats or ['png']

            slices_base_dir = output_dir / 'slices'
            slices_base_dir.mkdir(exist_ok=True)

            for design in designs:
                design_name = sanitize_filename(design.get('name', 'unknown'))
                sketch_path = get_design_output_path(designs_dir, design_name, keywords) / 'sketch.json'

                if not sketch_path.exists():
                    continue

                with open(sketch_path, 'r', encoding='utf-8') as f:
                    sketch_data = json.load(f)

                slices = extract_slices_from_sketch(sketch_data)
                if not slices:
                    continue

                # 获取设计所属的关键词分组
                design_group = get_design_group(design.get('name', ''), keywords)

                for slice_item in slices:
                    slice_name = sanitize_filename(slice_item['name'])
                    original_url = slice_item['url']
                    original_format = slice_item.get('format', 'png')

                    # 跳过 SVG（如果用户没有请求 SVG）
                    if original_format == 'svg' and 'svg' not in formats_to_export:
                        continue

                    for scale_name in scales_to_export:
                        for target_format in formats_to_export:
                            # 生成文件名
                            filename = get_slice_filename(
                                slice_name, platform, scale_name, target_format
                            )

                            # 生成输出路径
                            output_path = get_slice_output_path(
                                slices_base_dir,
                                platform,
                                design_group,
                                design_name,
                                scale_name,
                                filename
                            )

                            # 处理格式转换
                            if target_format == 'svg' and original_format == 'svg':
                                # SVG 直接下载
                                success = await download_file(api.client, original_url, output_path)
                            else:
                                # 下载 PNG
                                png_data = await download_file_bytes(api.client, original_url)
                                if png_data:
                                    # 格式转换
                                    converted = convert_format(png_data, target_format)
                                    output_path.parent.mkdir(parents=True, exist_ok=True)
                                    with open(output_path, 'wb') as f:
                                        f.write(converted)
                                    success = True
                                else:
                                    success = False

                            if success:
                                slice_count += 1
```

- [ ] **Step 2: 添加 download_file_bytes 辅助函数**

在 `download_file` 函数后添加：

```python
async def download_file_bytes(
    client: httpx.AsyncClient,
    url: str,
    max_retries: int = 3
) -> bytes:
    """
    下载文件到内存

    Args:
        client: HTTP 客户端
        url: 文件 URL
        max_retries: 最大重试次数

    Returns:
        文件数据，失败返回 None
    """
    delay = 1.0
    for attempt in range(max_retries):
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.content
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
                delay *= 2
            else:
                return None
    return None
```

- [ ] **Step 3: 提交**

```bash
git add skills/export-lanhu/scripts/export_lanhu.py
git commit -m "feat(export): add platform and format support for slice downloads"
```

---

## Task 9: 更新 meta.json 生成

**Files:**
- Modify: `skills/export-lanhu/scripts/export_lanhu.py`

- [ ] **Step 1: 更新 meta.json 内容**

将 `# 7. 生成 meta.json` 部分改为：

```python
        # 7. 生成 meta.json
        # 计算各分组统计
        groups_stats = {}
        for design in designs:
            design_name = design.get('name', '')
            group = get_design_group(design_name, keywords)
            if group not in groups_stats:
                groups_stats[group] = {'design_count': 0, 'slice_count': 0}
            groups_stats[group]['design_count'] += 1

        meta = {
            'source_url': url,
            'project_name': project_name,
            'project_id': project_id,
            'export_time': datetime.now().isoformat(),
            'version_id': pages_data.get('version_id', '') if pages_data else '',
            'page_count': page_count,
            'design_count': len(designs),
            'slice_count': slice_count,
            # 新增字段
            'platform': platform,
            'keywords': keywords or [],
            'groups': groups_stats,
            'formats': target_formats or ['png'],
            'scales': target_scales or ['default'],
        }
        with open(output_dir / 'meta.json', 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
```

- [ ] **Step 2: 提交**

```bash
git add skills/export-lanhu/scripts/export_lanhu.py
git commit -m "feat(export): update meta.json with platform and grouping info"
```

---

## Task 10: 更新 main 函数调用

**Files:**
- Modify: `skills/export-lanhu/scripts/export_lanhu.py`

- [ ] **Step 1: 更新 main 函数中的 export_lanhu 调用**

将 `# 运行导出` 部分改为：

```python
    # 解析 --select 参数
    selection_indices = None
    if args.select:
        # 需要先获取总数
        list_result = asyncio.run(list_designs(
            url=args.url,
            cookie=config['cookie'],
            keywords=keywords,
            timeout=config.get('timeout', 30)
        ))
        total_matched = list_result['matched_count'] if keywords else list_result['total']
        try:
            selection_indices = parse_selection(args.select, total_matched)
        except SelectionParseError as e:
            print(f"❌ Invalid selection: {e}")
            sys.exit(1)

    # 运行导出
    result = asyncio.run(export_lanhu(
        url=args.url,
        output_base_dir=output_base_dir,
        cookie=config['cookie'],
        include_slices=not args.no_slices and config.get('include_slices', True),
        include_preview=not args.no_preview and config.get('include_preview', True),
        timeout=config.get('timeout', 30),
        keywords=keywords,
        design_ids=design_ids,
        # 新增参数
        selection=selection_indices,
        platform=args.platform,
        target_scales=target_scales,
        target_formats=target_formats
    ))
```

- [ ] **Step 2: 提交**

```bash
git add skills/export-lanhu/scripts/export_lanhu.py
git commit -m "feat(export): integrate new parameters in main function"
```

---

## Task 11: 更新 SKILL.md

**Files:**
- Modify: `skills/export-lanhu/SKILL.md`

- [ ] **Step 1: 更新 SKILL.md 内容**

在 `## 可选参数` 部分后添加：

```markdown
## 增强功能参数

| 参数 | 说明 |
|------|------|
| `--select <表达式>` | 选择表达式，跳过交互确认 |
| `--platform <平台>` | 目标平台 (ios/android/web)，默认 ios |
| `--scales <比例>` | 切图比例 (all 或指定)，默认 all |
| `--formats <格式>` | 切图格式 (png,webp,svg)，默认 png |

### 选择表达式语法

```
表达式              说明
─────────────────────────────────────
1,3,5              选择第 1、3、5 个
1-5                选择第 1 到 5 个
1-5,8,10           范围和单选组合
1-5 -2,4           选择 1-5 但排除 2 和 4
*                  全选
^2,4               全选后排除 2 和 4
```

### 平台配置

| 平台 | 倍率 | 默认倍率 | 文件命名 |
|------|------|----------|----------|
| iOS | 1x, 2x, 3x | 3x | icon@3x.png |
| Android | mdpi~xxxhdpi | xxxhdpi | drawable-xxxhdpi/icon.png |
| Web | 1x, 2x | 2x | icon@2x.png |

### 输出目录结构（增强）

```
{项目名}-{时间}/
├── designs/
│   ├── 登录/                    # 按关键词分组
│   │   └── 01-登录页/
│   │       ├── schema.json
│   │       ├── sketch.json
│   │       └── preview.png
│   └── _其他/                   # 未匹配关键词的设计
├── slices/
│   └── iOS/                     # 按平台分组
│       └── 登录/                # 按关键词分组
│           └── 01-登录页/
│               ├── icon@2x.png
│               └── icon@3x.png
├── meta.json
└── README.md
```

## 示例场景

**场景 1：导出登录相关设计，选择前 4 个**
```
用户：导出蓝湖 <URL> 登录相关的页面数据
Claude：预览 → 展示匹配结果 → 用户输入 "1-4" → 导出
```

**场景 2：导出 Android 平台切图**
```
用户：导出蓝湖 <URL> 登录相关设计，Android 平台
Claude：--platform android --scales all
```

**场景 3：导出 WebP 格式切图**
```
用户：导出蓝湖 <URL> 登录相关设计，WebP 格式
Claude：--formats webp
```
```

- [ ] **Step 2: 提交**

```bash
git add skills/export-lanhu/SKILL.md
git commit -m "docs(skill): update SKILL.md with enhanced features"
```

---

## Task 12: 集成测试

**Files:**
- Test: `skills/export-lanhu/scripts/test_integration.py`

- [ ] **Step 1: 运行完整测试**

```bash
cd skills/export-lanhu/scripts
python -m pytest test_*.py -v
```

Expected: All tests pass

- [ ] **Step 2: 手动测试 --list 模式**

```bash
python export_lanhu.py "<测试URL>" --keyword 登录 --list
```

Expected: 输出有效的 JSON

- [ ] **Step 3: 手动测试选择表达式**

```bash
python export_lanhu.py "<测试URL>" --keyword 登录 --select "1-2" --platform ios --formats png --no-slices
```

Expected: 只导出前 2 个匹配的设计

- [ ] **Step 4: 手动测试平台切换**

```bash
python export_lanhu.py "<测试URL>" --keyword 登录 --select "1" --platform android --formats png,webp --no-preview
```

Expected: 切图保存到 drawable-* 目录

---

## 验收标准

- [ ] `--select` 参数支持组合选择语法
- [ ] `--platform` 参数正常切换 iOS/Android/Web
- [ ] `--scales` 参数控制切图倍率
- [ ] `--formats` 参数支持多格式导出
- [ ] 有关键词时按关键词分组保存
- [ ] 无关键词时不分组（向后兼容）
- [ ] 错误处理：网络重试、格式转换失败回退
- [ ] meta.json 包含平台和分组信息
- [ ] 所有单元测试通过
