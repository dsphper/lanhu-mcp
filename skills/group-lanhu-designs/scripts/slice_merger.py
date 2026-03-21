"""
切图合并器 - 合并同名切图，保留最大尺寸
"""
from pathlib import Path
from collections import defaultdict
import re
from models import Slice


def extract_scale(name: str) -> float:
    """从文件名提取缩放比例"""
    match = re.search(r'@(\d+)x$', name)
    if match:
        return float(match.group(1))
    return 1.0


def collect_slices(export_dir: Path, page_names: list[str]) -> list[Slice]:
    """
    收集指定页面的切图

    Args:
        export_dir: 导出目录
        page_names: 页面名称列表

    Returns:
        切图列表
    """
    from PIL import Image

    slices = []
    image_extensions = {'.png', '.jpg', '.jpeg', '.webp'}

    for page_name in page_names:
        # 查找 slices 目录
        slices_dir = export_dir / 'slices' / page_name
        if not slices_dir.exists():
            continue

        for img_file in slices_dir.rglob('*'):
            if img_file.suffix.lower() not in image_extensions:
                continue

            # 使用 PIL 读取图片尺寸
            width, height = 0, 0
            try:
                with Image.open(img_file) as img:
                    width, height = img.size
            except Exception:
                pass  # 无法读取时保持 0,0

            scale = extract_scale(img_file.stem)

            slices.append(Slice(
                name=img_file.stem,
                path=img_file,
                width=width,
                height=height,
                page_name=page_name,
                scale=scale
            ))

    return slices


def merge_slices(slices: list[Slice]) -> list[Slice]:
    """
    合并同名切图

    Args:
        slices: 所有切图列表

    Returns:
        合并后的切图列表（每个基础名称只保留一个）
    """
    if not slices:
        return []

    # 按基础名称分组
    by_base_name: dict[str, list[Slice]] = defaultdict(list)
    for s in slices:
        base = s.base_name
        by_base_name[base].append(s)

    result = []
    for base_name, versions in by_base_name.items():
        if len(versions) == 1:
            result.append(versions[0])
        else:
            # 按面积降序排序，保留最大
            versions.sort(key=lambda s: s.area, reverse=True)
            largest = versions[0]
            # 记录所有来源
            largest.sources = [
                (v.page_name, v.width, v.height, v.scale)
                for v in versions
            ]
            result.append(largest)

    return result


def copy_merged_slices(slices: list[Slice], output_dir: Path) -> int:
    """
    复制合并后的切图到输出目录

    Args:
        slices: 合并后的切图列表
        output_dir: 输出目录

    Returns:
        复制的文件数
    """
    import shutil

    output_dir.mkdir(parents=True, exist_ok=True)
    count = 0

    for s in slices:
        if not s.path.exists():
            continue
        dest = output_dir / s.path.name
        if not dest.exists():
            shutil.copy2(s.path, dest)
            count += 1

    return count
