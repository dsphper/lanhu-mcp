"""
group_designs.py - 蓝湖设计分组主入口

将相关联的蓝湖设计页面分组并合并分析
"""
import argparse
import sys
from pathlib import Path

from page_grouper import group_pages, find_sketch_files
from slice_merger import collect_slices, merge_slices, copy_merged_slices
from merged_generator import MergedGenerator


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description='分组并合并蓝湖设计页面'
    )
    parser.add_argument(
        'export_dir',
        type=str,
        help='export-lanhu 导出的目录路径'
    )
    parser.add_argument(
        '--framework', '-f',
        type=str,
        default='html',
        choices=['html', 'vue', 'react', 'flutter', 'miniprogram', 'uniapp'],
        help='目标框架 (默认: html)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='自定义输出目录（默认: {export_dir}/grouped/）'
    )
    parser.add_argument(
        '--no-slices',
        action='store_true',
        help='不合并切图'
    )

    args = parser.parse_args()

    # 验证目录
    export_dir = Path(args.export_dir)
    if not export_dir.exists():
        print(f"错误: 目录不存在: {export_dir}", file=sys.stderr)
        sys.exit(1)

    # 设置输出目录
    output_dir = Path(args.output) if args.output else export_dir / 'grouped'
    output_dir.mkdir(parents=True, exist_ok=True)

    # 查找 sketch.json 文件
    sketch_files = find_sketch_files(export_dir)

    if not sketch_files:
        print(f"警告: 未找到 sketch.json 文件: {export_dir}", file=sys.stderr)
        sys.exit(0)

    page_names = [name for name, _ in sketch_files]

    print(f"找到 {len(page_names)} 个设计页面")

    # 分组
    groups = group_pages(page_names)

    print(f"识别到 {len(groups)} 个分组")

    # 生成合并文档
    generator = MergedGenerator(args.framework)

    total_slices = 0
    for group in groups:
        print(f"  分组 \"{group.group_key}\": {len(group.pages)} 个页面")

        # 收集并合并切图
        if not args.no_slices:
            all_slices = collect_slices(export_dir, [p.original for p in group.pages])
            merged_slices = merge_slices(all_slices)

            # 复制切图
            group_slice_dir = output_dir / group.group_key / 'slices'
            copied = copy_merged_slices(merged_slices, group_slice_dir)
            total_slices += copied
        else:
            merged_slices = []

        # 生成文档
        doc = generator.generate(group, merged_slices)
        doc_file = output_dir / group.group_key / f"{group.group_name}-合并分析.md"
        doc_file.parent.mkdir(parents=True, exist_ok=True)

        with open(doc_file, 'w', encoding='utf-8') as f:
            f.write(doc)

        print(f"    -> 生成: {doc_file}")

    print("-" * 50)
    print(f"完成! 输出目录: {output_dir}")
    if not args.no_slices:
        print(f"切图合并: {total_slices} 个")


if __name__ == '__main__':
    main()
