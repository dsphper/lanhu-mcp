"""
analyze_design.py - 蓝湖设计分析主入口

解析 sketch.json，生成 UI 布局描述文档
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Any

from layer_parser import LayerParser, ParseError
from layout_analyzer import LayoutAnalyzer
from style_extractor import StyleExtractor
from markdown_generator import MarkdownGenerator


def find_sketch_files(export_dir: Path) -> list[Path]:
    """
    查找所有 sketch.json 文件

    Args:
        export_dir: 导出目录

    Returns:
        sketch.json 文件路径列表
    """
    sketch_files = []

    # 查找所有 sketch.json
    for sketch_file in export_dir.rglob('sketch.json'):
        # 排除 analysis 目录
        if 'analysis' not in sketch_file.parts:
            sketch_files.append(sketch_file)

    return sorted(sketch_files)


def collect_slices(export_dir: Path, design_name: str) -> list[tuple[str, str, int, int]]:
    """
    收集切图资源

    Args:
        export_dir: 导出目录
        design_name: 设计图名称

    Returns:
        切片列表 [(name, path, width, height), ...]
    """
    slices = []

    # 查找 slices 目录
    slices_dir = export_dir / 'slices' / design_name
    if not slices_dir.exists():
        # 尝试其他可能的位置
        for candidate in export_dir.rglob(f'slices/{design_name}'):
            slices_dir = candidate
            break

    if not slices_dir.exists():
        return slices

    # 收集所有切图
    for img_file in slices_dir.rglob('*'):
        if img_file.suffix.lower() in ('.png', '.jpg', '.jpeg', '.svg', '.webp'):
            # 尝试从 schema.json 获取尺寸信息
            width, height = 0, 0
            schema_file = img_file.with_suffix('.json')
            if schema_file.exists():
                try:
                    with open(schema_file, 'r', encoding='utf-8') as f:
                        schema = json.load(f)
                        width = schema.get('width', 0)
                        height = schema.get('height', 0)
                except (json.JSONDecodeError, IOError):
                    pass

            rel_path = img_file.relative_to(export_dir)
            slices.append((
                img_file.stem,
                str(rel_path).replace('\\', '/'),
                width,
                height
            ))

    return slices


def analyze_design(
    sketch_path: Path,
    export_dir: Path,
    framework: str,
    output_dir: Path
) -> dict[str, Any]:
    """
    分析单个设计图

    Args:
        sketch_path: sketch.json 文件路径
        export_dir: 导出根目录
        framework: 目标框架
        output_dir: 输出目录

    Returns:
        分析结果统计
    """
    print(f"分析: {sketch_path.parent.name}/{sketch_path.parent.parent.name}")

    # 1. 解析图层
    parser = LayerParser(sketch_path)
    root = parser.parse()
    meta = parser.get_meta()

    # 2. 布局分析
    layout_analyzer = LayoutAnalyzer(root)

    # 3. 样式提取
    style_extractor = StyleExtractor(root)

    # 4. 生成 Markdown
    generator = MarkdownGenerator(framework)

    # 生成布局分析文档
    layout_md = generator.generate_layout_analysis(
        root, layout_analyzer, style_extractor, meta
    )

    # 收集切图
    design_name = sketch_path.parent.name
    slices = collect_slices(export_dir, design_name)
    slices_md = generator.generate_slices_md(slices)

    # 生成样式摘要
    colors = style_extractor.get_top_colors(20)
    fonts = style_extractor.get_top_fonts(20)
    styles_md = generator.generate_styles_md(colors, fonts)

    # 5. 保存输出
    output_file = output_dir / f"{design_name}-layout.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(layout_md)
        f.write('\n\n---\n\n')
        f.write(slices_md)
        f.write('\n\n---\n\n')
        f.write(styles_md)

    return {
        'name': design_name,
        'layers': layout_analyzer.get_all_hints().__len__(),
        'colors': len(colors),
        'fonts': len(fonts),
        'slices': len(slices),
        'output': str(output_file)
    }


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description='分析蓝湖设计数据，生成 UI 布局描述文档'
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
        '--design', '-d',
        type=str,
        default=None,
        help='指定设计图名称（可选，默认处理所有）'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='自定义输出目录（默认: {export_dir}/analysis/）'
    )

    args = parser.parse_args()

    # 验证目录
    export_dir = Path(args.export_dir)
    if not export_dir.exists():
        print(f"错误: 目录不存在: {export_dir}", file=sys.stderr)
        sys.exit(1)

    # 设置输出目录
    output_dir = Path(args.output) if args.output else export_dir / 'analysis'
    output_dir.mkdir(parents=True, exist_ok=True)

    # 查找 sketch.json 文件
    sketch_files = find_sketch_files(export_dir)

    if not sketch_files:
        print(f"警告: 未找到 sketch.json 文件: {export_dir}", file=sys.stderr)
        sys.exit(0)

    # 过滤指定设计
    if args.design:
        sketch_files = [
            f for f in sketch_files
            if args.design.lower() in f.parent.name.lower()
        ]
        if not sketch_files:
            print(f"错误: 未找到匹配的设计图: {args.design}", file=sys.stderr)
            sys.exit(1)

    print(f"找到 {len(sketch_files)} 个设计图")
    print(f"目标框架: {args.framework}")
    print(f"输出目录: {output_dir}")
    print("-" * 50)

    # 分析每个设计
    results = []
    for sketch_path in sketch_files:
        try:
            result = analyze_design(
                sketch_path,
                export_dir,
                args.framework,
                output_dir
            )
            results.append(result)
            print(f"  ✓ 生成: {result['output']}")
        except ParseError as e:
            print(f"  ✗ 解析错误: {e}", file=sys.stderr)
        except Exception as e:
            print(f"  ✗ 未知错误: {e}", file=sys.stderr)

    # 输出统计
    print("-" * 50)
    print(f"完成! 共处理 {len(results)} 个设计图")

    if results:
        print("\n统计:")
        print(f"  - 颜色变量: {sum(r['colors'] for r in results)} 个")
        print(f"  - 字体样式: {sum(r['fonts'] for r in results)} 个")
        print(f"  - 切图资源: {sum(r['slices'] for r in results)} 个")


if __name__ == '__main__':
    main()
