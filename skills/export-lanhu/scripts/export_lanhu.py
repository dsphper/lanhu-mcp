#!/usr/bin/env python3
"""
蓝湖数据导出脚本

用法:
    python export_lanhu.py <URL> [--output <目录>] [--no-slices] [--no-preview]
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

import httpx

from lanhu_api import LanhuAPI


def load_config(project_root: Path) -> dict:
    """
    从项目的 .claude/lanhu.config.json 加载配置

    Args:
        project_root: 项目根目录

    Returns:
        配置字典
    """
    config_path = project_root / ".claude" / "lanhu.config.json"

    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_path}\n"
            "Please create .claude/lanhu.config.json with your Lanhu cookie."
        )

    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def sanitize_filename(name: str) -> str:
    """清理文件名，移除非法字符"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    return name.strip()


def generate_output_dir(project_name: str, base_dir: Path) -> Path:
    """
    生成输出目录路径

    格式: {base_dir}/{项目名}-{yyyyMMddHH}/
    """
    timestamp = datetime.now().strftime('%Y%m%d%H')
    safe_name = sanitize_filename(project_name)
    return base_dir / f"{safe_name}-{timestamp}"


async def download_file(client: httpx.AsyncClient, url: str, output_path: Path) -> bool:
    """
    下载文件

    Args:
        client: HTTP 客户端
        url: 文件 URL
        output_path: 输出路径

    Returns:
        是否成功
    """
    try:
        response = await client.get(url)
        response.raise_for_status()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(response.content)
        return True
    except Exception as e:
        print(f"  ⚠️ Failed to download {url}: {e}")
        return False


async def download_design_data(
    api: LanhuAPI,
    design: dict,
    output_dir: Path,
    include_preview: bool
) -> dict:
    """
    下载单个设计的数据

    Args:
        api: API 客户端
        design: 设计信息
        output_dir: 输出目录
        include_preview: 是否下载预览图

    Returns:
        下载结果
    """
    design_name = sanitize_filename(design.get('name', 'unknown'))
    design_dir = output_dir / design_name
    design_dir.mkdir(parents=True, exist_ok=True)

    result = {
        'name': design_name,
        'schema': False,
        'sketch': False,
        'preview': False
    }

    # 下载 Schema JSON
    try:
        schema = await api.get_design_schema_json(
            design['id'],
            design.get('team_id', ''),
            design.get('project_id', '')
        )
        with open(design_dir / 'schema.json', 'w', encoding='utf-8') as f:
            json.dump(schema, f, ensure_ascii=False, indent=2)
        result['schema'] = True
    except Exception as e:
        print(f"  ⚠️ Failed to get schema for {design_name}: {e}")

    # 下载 Sketch JSON
    try:
        sketch = await api.get_sketch_json(
            design['id'],
            design.get('team_id', ''),
            design.get('project_id', '')
        )
        with open(design_dir / 'sketch.json', 'w', encoding='utf-8') as f:
            json.dump(sketch, f, ensure_ascii=False, indent=2)
        result['sketch'] = True
    except Exception as e:
        print(f"  ⚠️ Failed to get sketch for {design_name}: {e}")

    # 下载预览图
    if include_preview and design.get('url'):
        preview_url = design['url'].split('?')[0]
        success = await download_file(
            api.client,
            preview_url,
            design_dir / 'preview.png'
        )
        result['preview'] = success

    return result


def generate_readme(output_dir: Path, meta: dict, pages: list, designs: list):
    """生成 README.md"""
    content = f"""# {meta['project_name']} - 蓝湖设计数据

## 基本信息

- **项目名称**: {meta['project_name']}
- **数据来源**: {meta['source_url']}
- **导出时间**: {meta['export_time']}
- **版本 ID**: {meta['version_id'][:8] if meta.get('version_id') else 'N/A'}...

## 数据统计

| 类型 | 数量 |
|------|------|
| 页面 | {meta['page_count']} |
| 设计图 | {meta['design_count']} |
| 切图 | {meta['slice_count']} |

## 目录结构

```
{output_dir.name}/
├── pages/           # 页面数据
├── designs/         # 设计图数据
├── slices/          # 切图资源
├── meta.json        # 元数据
└── README.md        # 说明文档
```

## 使用说明

1. 页面数据位于 `pages/` 目录，每个页面包含 `page.json`
2. 设计数据位于 `designs/` 目录，每个设计包含 `schema.json`、`sketch.json`、`preview.png`
3. 切图资源位于 `slices/` 目录
"""
    with open(output_dir / 'README.md', 'w', encoding='utf-8') as f:
        f.write(content)


async def export_lanhu(
    url: str,
    output_base_dir: Path,
    cookie: str,
    include_slices: bool = True,
    include_preview: bool = True,
    timeout: int = 30
) -> dict:
    """
    导出蓝湖数据

    Args:
        url: 蓝湖 URL
        output_base_dir: 输出根目录
        cookie: 蓝湖 Cookie
        include_slices: 是否下载切图
        include_preview: 是否下载预览图
        timeout: 超时秒数

    Returns:
        导出结果
    """
    api = LanhuAPI(cookie, timeout)

    try:
        # 1. 获取页面列表
        print("📄 Fetching pages list...")
        pages_data = await api.get_pages_list(url)
        project_name = pages_data.get('document_name', 'Unknown')

        # 2. 生成输出目录
        output_dir = generate_output_dir(project_name, output_base_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Output directory: {output_dir}")

        # 3. 保存页面数据
        print("📝 Saving pages data...")
        pages_dir = output_dir / 'pages'
        pages_dir.mkdir(exist_ok=True)

        for page in pages_data.get('pages', []):
            page_dir = pages_dir / sanitize_filename(page['name'])
            page_dir.mkdir(exist_ok=True)

            with open(page_dir / 'page.json', 'w', encoding='utf-8') as f:
                json.dump(page, f, ensure_ascii=False, indent=2)

        # 4. 获取设计列表
        print("🎨 Fetching designs list...")
        designs = await api.get_design_list(
            pages_data['team_id'],
            pages_data['project_id']
        )

        # 5. 下载设计数据
        print(f"📦 Downloading {len(designs)} designs...")
        designs_dir = output_dir / 'designs'
        designs_dir.mkdir(exist_ok=True)

        design_results = []
        for i, design in enumerate(designs, 1):
            print(f"  [{i}/{len(designs)}] {design.get('name', 'unknown')}")
            design['team_id'] = pages_data['team_id']
            design['project_id'] = pages_data['project_id']
            result = await download_design_data(
                api, design, designs_dir, include_preview
            )
            design_results.append(result)

        # 6. 下载切图
        slice_count = 0
        if include_slices:
            print("🖼️ Downloading slices...")
            slices_dir = output_dir / 'slices'
            slices_dir.mkdir(exist_ok=True)

            for design in designs:
                slices = await api.get_slices_info(
                    design['id'],
                    pages_data['team_id'],
                    pages_data['project_id']
                )
                for slice_item in slices:
                    slice_name = f"{sanitize_filename(slice_item['name'])}_{slice_item['scale']}.png"
                    success = await download_file(
                        api.client,
                        slice_item['url'],
                        slices_dir / slice_name
                    )
                    if success:
                        slice_count += 1

        # 7. 生成 meta.json
        meta = {
            'source_url': url,
            'project_name': project_name,
            'project_id': pages_data['project_id'],
            'export_time': datetime.now().isoformat(),
            'version_id': pages_data.get('version_id', ''),
            'page_count': len(pages_data.get('pages', [])),
            'design_count': len(designs),
            'slice_count': slice_count
        }
        with open(output_dir / 'meta.json', 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        # 8. 生成 README.md
        generate_readme(output_dir, meta, pages_data.get('pages', []), designs)

        print(f"\n✅ Export completed!")
        print(f"   Pages: {meta['page_count']}")
        print(f"   Designs: {meta['design_count']}")
        print(f"   Slices: {meta['slice_count']}")

        return {
            'success': True,
            'output_dir': str(output_dir),
            'meta': meta
        }

    finally:
        await api.close()


def main():
    parser = argparse.ArgumentParser(description='导出蓝湖设计数据')
    parser.add_argument('url', help='蓝湖 URL')
    parser.add_argument('--output', '-o', help='自定义输出目录')
    parser.add_argument('--no-slices', action='store_true', help='跳过切图下载')
    parser.add_argument('--no-preview', action='store_true', help='跳过预览图下载')

    args = parser.parse_args()

    # 查找项目根目录（当前目录或父目录）
    project_root = Path.cwd()

    # 加载配置
    try:
        config = load_config(project_root)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)

    # 确定输出目录
    output_base_dir = Path(args.output) if args.output else Path(config.get('output_base_dir', 'docs/lanhu/pages'))

    # 运行导出
    result = asyncio.run(export_lanhu(
        url=args.url,
        output_base_dir=output_base_dir,
        cookie=config['cookie'],
        include_slices=not args.no_slices and config.get('include_slices', True),
        include_preview=not args.no_preview and config.get('include_preview', True),
        timeout=config.get('timeout', 30)
    ))

    if not result['success']:
        sys.exit(1)


if __name__ == '__main__':
    main()
