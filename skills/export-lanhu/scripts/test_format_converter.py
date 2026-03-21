# test_format_converter.py
import pytest
from io import BytesIO
from PIL import Image
import random

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

    @pytest.fixture
    def complex_png(self):
        """创建复杂 PNG 图片（带渐变和随机噪点）"""
        img = Image.new('RGBA', (100, 100))
        pixels = img.load()
        random.seed(42)  # 固定种子确保可重复
        for x in range(100):
            for y in range(100):
                # 创建渐变 + 随机噪点
                r = (x * 2 + random.randint(0, 30)) % 256
                g = (y * 2 + random.randint(0, 30)) % 256
                b = ((x + y) + random.randint(0, 30)) % 256
                a = 200 + random.randint(0, 55)
                pixels[x, y] = (r, g, b, a)
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

    def test_webp_quality(self, complex_png):
        """WebP 质量参数（使用复杂图片测试）"""
        result_low = convert_format(complex_png, 'webp', quality=50)
        result_high = convert_format(complex_png, 'webp', quality=100)
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
