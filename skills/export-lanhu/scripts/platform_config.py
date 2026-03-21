"""
平台配置模块

支持 iOS、Android、Web 三种平台的切图配置
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Literal


PlatformName = Literal['ios', 'android', 'web']
Platform = PlatformName  # Alias for backward compatibility


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


def validate_scales(platform: str, scales: list) -> List[str]:
    """
    验证并过滤有效的 scale 值

    Args:
        platform: 平台名称
        scales: 用户提供的 scale 列表

    Returns:
        有效的 scale 列表（只保留平台支持的 scale）
    """
    config = get_platform_config(platform)
    valid_scales = []
    for scale in scales:
        if scale in config.scales:
            valid_scales.append(scale)
        else:
            print(f"⚠️ Invalid scale '{scale}' for platform {platform}, skipping")
    return valid_scales if valid_scales else [config.default_scale]
