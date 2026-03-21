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
