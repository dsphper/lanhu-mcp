"""
页面分组器 - 将相关联的页面分组
"""
from collections import defaultdict
from pathlib import Path
from models import ParsedPageName, PageGroup, TYPE_ORDER
from name_parser import parse_page_name


def group_pages(page_names: list[str]) -> list[PageGroup]:
    """
    将页面名称分组

    Args:
        page_names: 页面名称列表

    Returns:
        分组列表
    """
    # 解析所有页面名称
    parsed = [parse_page_name(name) for name in page_names]

    # 按分组键分组
    groups: dict[str, list[ParsedPageName]] = defaultdict(list)
    for p in parsed:
        groups[p.group_key].append(p)

    # 对每个分组内的页面排序
    result = []
    for group_key, pages in groups.items():
        # 排序：main -> popup -> state -> variant
        pages.sort(key=lambda p: (
            TYPE_ORDER.get(p.page_type, 99),
            p.sub_page or "",
            p.state or "",
            p.variant or 0
        ))

        # 获取业务顺序和分组名（从第一个页面）
        first = pages[0]
        result.append(PageGroup(
            group_key=group_key,
            business_order=first.business_order,
            group_name=first.group_name,
            pages=pages
        ))

    # 按业务顺序排序分组
    result.sort(key=lambda g: (
        g.business_order is not None,  # 有业务顺序的排前面
        int(g.business_order) if g.business_order else 999,
        g.group_name
    ))

    return result


def find_sketch_files(export_dir: Path) -> list[tuple[str, Path]]:
    """
    查找所有 sketch.json 文件

    Args:
        export_dir: 导出目录

    Returns:
        [(页面名称, sketch.json路径), ...]
    """
    result = []
    for sketch_file in export_dir.rglob('sketch.json'):
        # 排除 analysis 和 grouped 目录
        if 'analysis' in sketch_file.parts or 'grouped' in sketch_file.parts:
            continue
        # 页面名称是父目录名
        page_name = sketch_file.parent.name
        result.append((page_name, sketch_file))

    return sorted(result, key=lambda x: x[0])
