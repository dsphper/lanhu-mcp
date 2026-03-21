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
