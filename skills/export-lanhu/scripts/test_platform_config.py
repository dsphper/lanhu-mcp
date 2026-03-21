# test_platform_config.py
import pytest
from pathlib import Path
from platform_config import (
    Platform,
    PlatformConfig,
    get_platform_config,
    get_slice_filename,
    get_slice_output_path,
    validate_scales
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


class TestValidateScales:
    """scale 验证测试"""

    def test_valid_ios_scales(self, capsys):
        """iOS 有效 scales"""
        result = validate_scales('ios', ['1x', '2x', '3x'])
        assert result == ['1x', '2x', '3x']

    def test_valid_android_scales(self, capsys):
        """Android 有效 scales"""
        result = validate_scales('android', ['mdpi', 'hdpi', 'xxxhdpi'])
        assert result == ['mdpi', 'hdpi', 'xxxhdpi']

    def test_partial_valid_scales(self, capsys):
        """部分有效的 scales"""
        result = validate_scales('ios', ['1x', 'invalid', '3x'])
        assert result == ['1x', '3x']
        # 检查警告输出
        captured = capsys.readouterr()
        assert "Invalid scale 'invalid'" in captured.out

    def test_all_invalid_scales_returns_default(self, capsys):
        """全部无效返回默认 scale"""
        result = validate_scales('ios', ['invalid1', 'invalid2'])
        assert result == ['3x']  # iOS default
        captured = capsys.readouterr()
        assert "Invalid scale 'invalid1'" in captured.out
        assert "Invalid scale 'invalid2'" in captured.out

    def test_empty_scales_returns_default(self, capsys):
        """空列表返回默认 scale"""
        result = validate_scales('android', [])
        assert result == ['xxxhdpi']  # Android default

    def test_android_invalid_scale(self, capsys):
        """Android 无效 scale 警告"""
        result = validate_scales('android', ['2x', '3x'])  # iOS scales on Android
        assert result == ['xxxhdpi']  # All invalid, return default
        captured = capsys.readouterr()
        assert "Invalid scale '2x'" in captured.out
        assert "Invalid scale '3x'" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
