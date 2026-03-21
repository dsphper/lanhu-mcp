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
from dataclasses import dataclass, field

import httpx

from lanhu_api import LanhuAPI
from selection_parser import parse_selection, SelectionParseError
from platform_config import (
    get_platform_config,
    get_slice_filename,
    get_slice_output_path,
    get_all_scales
)
from format_converter import convert_format, resize_to_scale


# ============ 错误处理 ============

class LanhuExportError(Exception):
    """导出错误基类"""
    pass


class AuthenticationError(LanhuExportError):
    """认证失败"""
    pass


class NetworkError(LanhuExportError):
    """网络错误（可重试）"""
    pass


class ResourceNotFoundError(LanhuExportError):
    """资源不存在（跳过）"""
    pass


@dataclass
class ExportResult:
    """导出结果统计"""
    success: bool
    output_dir: Path
    designs_total: int = 0
    designs_success: int = 0
    designs_failed: int = 0
    slices_total: int = 0
    slices_success: int = 0
    slices_failed: int = 0
    errors: list = field(default_factory=list)

    def add_error(self, error: str):
        """添加错误记录"""
        self.errors.append(error)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'success': self.success,
            'output_dir': str(self.output_dir),
            'designs': {
                'total': self.designs_total,
                'success': self.designs_success,
                'failed': self.designs_failed,
            },
            'slices': {
                'total': self.slices_total,
                'success': self.slices_success,
                'failed': self.slices_failed,
            },
            'errors': self.errors,
        }


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
    """清理文件名，移除非法字符和空格"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    # 替换空格为下划线
    name = name.replace(' ', '_')
    return name.strip()


def filter_designs_by_keywords(designs: list, keywords: list) -> tuple[list, list]:
    """
    根据关键词过滤设计列表

    Args:
        designs: 设计列表，每个元素包含 id 和 name
        keywords: 关键词列表（OR 逻辑，不区分大小写）

    Returns:
        (matched, unmatched) 元组
    """
    if not keywords:
        return designs, []

    # 统一转小写进行匹配
    keywords_lower = [kw.lower() for kw in keywords]

    matched = []
    unmatched = []

    for design in designs:
        name = design.get('name', '')
        name_lower = name.lower()

        # OR 逻辑：任一关键词匹配即可
        if any(kw in name_lower for kw in keywords_lower):
            matched.append(design)
        else:
            unmatched.append(design)

    return matched, unmatched


def get_design_group(design_name: str, keywords: list) -> str:
    """
    根据设计名和关键词确定分组

    Args:
        design_name: 设计图名称
        keywords: 过滤关键词列表

    Returns:
        分组名称（空字符串表示不分组）
    """
    # 无关键词时，不分组
    if not keywords:
        return ""

    for keyword in keywords:
        if keyword.lower() in design_name.lower():
            return keyword
    return "_其他"


def get_design_output_path(base_dir: Path, design_name: str, keywords: list) -> Path:
    """
    获取设计输出路径

    Args:
        base_dir: designs 基础目录
        design_name: 设计图名称（已清理）
        keywords: 过滤关键词列表

    Returns:
        设计输出路径
    """
    group = get_design_group(design_name, keywords)

    if group:
        # 有关键词分组
        return base_dir / group / design_name
    else:
        # 无关键词，不分组
        return base_dir / design_name


def output_design_list(
    source_url: str,
    project_name: str,
    project_id: str,
    designs: list,
    keywords: list,
    max_unmatched_samples: int = 10
) -> dict:
    """
    输出设计列表 JSON（用于 --list 模式）

    Args:
        source_url: 来源 URL
        project_name: 项目名称
        project_id: 项目 ID
        designs: 设计列表
        keywords: 过滤关键词
        max_unmatched_samples: 未匹配列表最大返回数量

    Returns:
        JSON 输出字典
    """
    matched, unmatched = filter_designs_by_keywords(designs, keywords)

    # 限制未匹配列表长度
    unmatched_samples = unmatched[:max_unmatched_samples]

    return {
        'source_url': source_url,
        'project_name': project_name,
        'project_id': project_id,
        'total': len(designs),
        'matched_count': len(matched),
        'matched': [{'id': d['id'], 'name': d['name']} for d in matched],
        'unmatched_count': len(unmatched),
        'unmatched': [{'id': d['id'], 'name': d['name']} for d in unmatched_samples]
    }


def extract_slices_from_sketch(sketch_data: dict) -> list:
    """
    从 sketch.json 中递归提取所有切图

    Args:
        sketch_data: sketch.json 数据

    Returns:
        切图列表，每个元素包含 name, url, width, height, format
    """
    slices = []

    def find_slices(obj, layer_path=""):
        """递归查找切图"""
        if not obj or not isinstance(obj, dict):
            return

        current_name = obj.get('name', 'unnamed')
        current_path = f"{layer_path}/{current_name}" if layer_path else current_name

        # 检查 image 字段 (PNG/SVG)
        if obj.get('image'):
            image_data = obj['image']
            # 优先使用 PNG，其次 SVG
            download_url = image_data.get('imageUrl') or image_data.get('svgUrl')
            if download_url:
                frame = obj.get('frame') or obj.get('bounds') or {}
                width = frame.get('width', 0)
                height = frame.get('height', 0)

                slices.append({
                    'name': current_name,
                    'url': download_url,
                    'width': int(width) if width else 0,
                    'height': int(height) if height else 0,
                    'format': 'png' if image_data.get('imageUrl') else 'svg',
                    'layer_path': current_path
                })

        # 检查 ddsImage 字段 (旧版兼容)
        elif obj.get('ddsImage') and obj['ddsImage'].get('imageUrl'):
            frame = obj.get('frame') or obj.get('bounds') or {}
            width = frame.get('width', 0)
            height = frame.get('height', 0)

            slices.append({
                'name': current_name,
                'url': obj['ddsImage']['imageUrl'],
                'width': int(width) if width else 0,
                'height': int(height) if height else 0,
                'format': 'png',
                'layer_path': current_path
            })

        # 递归处理子图层
        children = obj.get('layers') or obj.get('children') or []
        for child in children:
            find_slices(child, current_path)

    # 从新版结构 (artboard.layers) 提取
    if sketch_data.get('artboard') and sketch_data['artboard'].get('layers'):
        for layer in sketch_data['artboard']['layers']:
            find_slices(layer)

    # 从旧版结构 (info[]) 提取
    elif sketch_data.get('info'):
        for item in sketch_data['info']:
            find_slices(item)

    return slices


def generate_output_dir(project_name: str, base_dir: Path) -> Path:
    """
    生成输出目录路径

    格式: {base_dir}/{项目名}-{yyyyMMddHH}/
    """
    timestamp = datetime.now().strftime('%Y%m%d%H')
    safe_name = sanitize_filename(project_name)
    return base_dir / f"{safe_name}-{timestamp}"


async def download_file(
    client: httpx.AsyncClient,
    url: str,
    output_path: Path,
    max_retries: int = 3,
    initial_delay: float = 1.0
) -> bool:
    """
    下载文件（带重试）

    Args:
        client: HTTP 客户端
        url: 文件 URL
        output_path: 输出路径
        max_retries: 最大重试次数
        initial_delay: 初始延迟秒数

    Returns:
        是否成功
    """
    delay = initial_delay
    last_error = None

    for attempt in range(max_retries):
        try:
            response = await client.get(url)
            response.raise_for_status()

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(response.content)
            return True
        except httpx.TimeoutException as e:
            last_error = e
            if attempt < max_retries - 1:
                print(f"  ⚠️ Timeout, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(delay)
                delay *= 2  # 指数退避
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Authentication failed. Please check your Cookie.")
            if e.response.status_code == 404:
                print(f"  ⚠️ Resource not found: {url}")
                return False
            last_error = e
            if attempt < max_retries - 1:
                print(f"  ⚠️ HTTP error, retrying in {delay}s")
                await asyncio.sleep(delay)
                delay *= 2
        except Exception as e:
            print(f"  ⚠️ Failed to download {url}: {e}")
            return False

    print(f"  ⚠️ Failed after {max_retries} retries: {last_error}")
    return False


async def download_file_bytes(
    client: httpx.AsyncClient,
    url: str,
    max_retries: int = 3
) -> bytes:
    """
    下载文件到内存

    Args:
        client: HTTP 客户端
        url: 文件 URL
        max_retries: 最大重试次数

    Returns:
        文件数据，失败返回 None
    """
    delay = 1.0
    for attempt in range(max_retries):
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.content
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
                delay *= 2
            else:
                return None
    return None


async def download_design_data(
    api: LanhuAPI,
    design: dict,
    output_dir: Path,
    subdir_name: str = None,
    include_preview: bool = True
) -> dict:
    """
    下载单个设计的数据

    Args:
        api: API 客户端
        design: 设计信息
        output_dir: 输出目录
        subdir_name: 子目录名称（用于分组），为 None 时使用设计名
        include_preview: 是否下载预览图

    Returns:
        下载结果
    """
    design_name = sanitize_filename(design.get('name', 'unknown'))
    if subdir_name:
        design_dir = output_dir / subdir_name
    else:
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


async def list_designs(
    url: str,
    cookie: str,
    keywords: list = None,
    timeout: int = 30
) -> dict:
    """
    获取设计列表（用于 --list 模式）

    Args:
        url: 蓝湖 URL
        cookie: 蓝湖 Cookie
        keywords: 过滤关键词
        timeout: 超时秒数

    Returns:
        设计列表 JSON
    """
    api = LanhuAPI(cookie, timeout)

    try:
        # 解析 URL 参数
        params = api.parse_url(url)
        team_id = params['team_id']
        project_id = params['project_id']
        doc_id = params.get('doc_id')

        # 获取项目名称
        if doc_id:
            pages_data = await api.get_pages_list(url)
            project_name = pages_data.get('document_name', 'Unknown')
        else:
            project_name = f"DesignProject-{project_id[:8]}"

        # 获取设计列表
        designs = await api.get_design_list(team_id, project_id)

        # 输出 JSON
        result = output_design_list(
            source_url=url,
            project_name=project_name,
            project_id=project_id,
            designs=designs,
            keywords=keywords or []
        )

        return result

    finally:
        await api.close()


async def export_lanhu(
    url: str,
    output_base_dir: Path,
    cookie: str,
    include_slices: bool = True,
    include_preview: bool = True,
    timeout: int = 30,
    keywords: list = None,
    design_ids: list = None,
    # 新增参数
    selection: list = None,  # 选择后的索引列表
    platform: str = 'ios',
    target_scales: list = None,  # None 表示使用默认
    target_formats: list = None  # None 表示 ['png']
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
        # 解析 URL 参数
        params = api.parse_url(url)
        team_id = params['team_id']
        project_id = params['project_id']
        doc_id = params.get('doc_id')

        # 判断是否有文档 ID（原型文档 vs 设计图项目）
        pages_data = None
        page_count = 0

        if doc_id:
            # 1a. 获取页面列表（原型文档）
            print("📄 Fetching pages list...")
            pages_data = await api.get_pages_list(url)
            project_name = pages_data.get('document_name', 'Unknown')
            page_count = len(pages_data.get('pages', []))
        else:
            # 1b. 设计图项目，无页面
            print("📄 Design project (no pages)...")
            project_name = f"DesignProject-{project_id[:8]}"

        # 2. 生成输出目录
        output_dir = generate_output_dir(project_name, output_base_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Output directory: {output_dir}")

        # 3. 保存页面数据（如果有）
        if pages_data and pages_data.get('pages'):
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
        designs = await api.get_design_list(team_id, project_id)

        # 4.5 根据条件过滤设计
        if design_ids:
            # 按 ID 精确过滤
            designs = [d for d in designs if d['id'] in design_ids]
            print(f"🔍 Filtered by IDs: {len(designs)} designs")
        elif keywords:
            # 按关键词过滤
            matched, unmatched = filter_designs_by_keywords(designs, keywords)
            if selection is not None:
                # 在匹配结果中按索引选择
                designs = [matched[i] for i in selection if i < len(matched)]
                print(f"🔍 Selected {len(designs)} from {len(matched)} matched designs")
            else:
                designs = matched
                print(f"🔍 Filtered by keywords: {len(designs)} designs")
        elif selection is not None:
            # 无关键词，在全量设计中按索引选择
            designs = [designs[i] for i in selection if i < len(designs)]
            print(f"🔍 Selected {len(designs)} designs by index")

        if not designs:
            print("⚠️ No designs match the filter criteria")
            return {
                'success': True,
                'output_dir': str(output_dir),
                'meta': {
                    'source_url': url,
                    'project_name': project_name,
                    'project_id': project_id,
                    'export_time': datetime.now().isoformat(),
                    'design_count': 0,
                    'slice_count': 0
                }
            }

        # 5. 下载设计数据（按关键词分组）
        print(f"📦 Downloading {len(designs)} designs...")
        designs_dir = output_dir / 'designs'
        designs_dir.mkdir(exist_ok=True)

        design_results = []
        for i, design in enumerate(designs, 1):
            design_name = sanitize_filename(design.get('name', 'unknown'))
            design['team_id'] = team_id
            design['project_id'] = project_id

            # 获取分组路径
            design_output = get_design_output_path(designs_dir, design_name, keywords)
            design_output.mkdir(parents=True, exist_ok=True)

            print(f"  [{i}/{len(designs)}] {design.get('name', 'unknown')}")
            result = await download_design_data(
                api, design, design_output.parent, design_output.name, include_preview
            )
            design_results.append(result)

        # 6. 下载切图（按平台、关键词分组，支持多格式）
        slice_count = 0
        if include_slices:
            print("🖼️ Downloading slices...")
            platform_config = get_platform_config(platform)

            # 确定要导出的倍率
            if target_scales:
                scales_to_export = target_scales
            else:
                scales_to_export = [platform_config.default_scale]

            formats_to_export = target_formats or ['png']

            slices_base_dir = output_dir / 'slices'
            slices_base_dir.mkdir(exist_ok=True)

            for design in designs:
                design_name = sanitize_filename(design.get('name', 'unknown'))
                sketch_path = get_design_output_path(designs_dir, design_name, keywords) / 'sketch.json'

                if not sketch_path.exists():
                    continue

                with open(sketch_path, 'r', encoding='utf-8') as f:
                    sketch_data = json.load(f)

                slices = extract_slices_from_sketch(sketch_data)
                if not slices:
                    continue

                # 获取设计所属的关键词分组
                design_group = get_design_group(design.get('name', ''), keywords)

                for slice_item in slices:
                    slice_name = sanitize_filename(slice_item['name'])
                    original_url = slice_item['url']
                    original_format = slice_item.get('format', 'png')

                    # 跳过 SVG（如果用户没有请求 SVG）
                    if original_format == 'svg' and 'svg' not in formats_to_export:
                        continue

                    for scale_name in scales_to_export:
                        for target_format in formats_to_export:
                            # SVG 不需要缩放
                            if original_format == 'svg' and target_format == 'svg':
                                filename = get_slice_filename(
                                    slice_name, platform, scale_name, 'svg'
                                )
                                output_path = get_slice_output_path(
                                    slices_base_dir,
                                    platform,
                                    design_group,
                                    design_name,
                                    scale_name,
                                    filename
                                )
                                success = await download_file(api.client, original_url, output_path)
                                if success:
                                    slice_count += 1
                                continue

                            # 下载 PNG
                            png_data = await download_file_bytes(api.client, original_url)
                            if not png_data:
                                continue

                            # 格式转换
                            converted = convert_format(png_data, target_format)

                            # 生成文件名和路径
                            filename = get_slice_filename(
                                slice_name, platform, scale_name, target_format
                            )
                            output_path = get_slice_output_path(
                                slices_base_dir,
                                platform,
                                design_group,
                                design_name,
                                scale_name,
                                filename
                            )

                            output_path.parent.mkdir(parents=True, exist_ok=True)
                            with open(output_path, 'wb') as f:
                                f.write(converted)
                            slice_count += 1

        # 7. 生成 meta.json
        # 计算各分组统计
        groups_stats = {}
        for design in designs:
            design_name = design.get('name', '')
            group = get_design_group(design_name, keywords)
            if group not in groups_stats:
                groups_stats[group] = {'design_count': 0, 'slice_count': 0}
            groups_stats[group]['design_count'] += 1

        meta = {
            'source_url': url,
            'project_name': project_name,
            'project_id': project_id,
            'export_time': datetime.now().isoformat(),
            'version_id': pages_data.get('version_id', '') if pages_data else '',
            'page_count': page_count,
            'design_count': len(designs),
            'slice_count': slice_count,
            # 新增字段
            'platform': platform,
            'keywords': keywords or [],
            'groups': groups_stats,
            'formats': target_formats or ['png'],
            'scales': target_scales or ['default'],
        }
        with open(output_dir / 'meta.json', 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        # 8. 生成 README.md
        pages_list = pages_data.get('pages', []) if pages_data else []
        generate_readme(output_dir, meta, pages_list, designs)

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


def find_project_root(start_path: Path = None) -> Path:
    """
    从给定路径向上查找项目根目录（包含 .claude 文件夹的目录）

    Args:
        start_path: 起始路径，默认为当前工作目录

    Returns:
        项目根目录路径

    Raises:
        FileNotFoundError: 如果找不到项目根目录
    """
    if start_path is None:
        start_path = Path.cwd()

    current = start_path.resolve()

    while current != current.parent:
        if (current / '.claude').is_dir():
            return current
        current = current.parent

    # 如果到达根目录都没找到，返回当前目录
    return start_path


def main():
    parser = argparse.ArgumentParser(description='导出蓝湖设计数据')
    parser.add_argument('url', help='蓝湖 URL')
    parser.add_argument('--output', '-o', help='自定义输出目录')
    parser.add_argument('--no-slices', action='store_true', help='跳过切图下载')
    parser.add_argument('--no-preview', action='store_true', help='跳过预览图下载')

    # 新增参数
    parser.add_argument('--list', action='store_true',
                        help='只列出设计，不下载，输出 JSON')
    parser.add_argument('--keyword', type=str,
                        help='过滤关键词（逗号分隔多个，OR 逻辑）')
    parser.add_argument('--keywords', nargs='+',
                        help='过滤关键词（空格分隔多个）')
    parser.add_argument('--ids', type=str,
                        help='指定设计 ID 导出（逗号分隔，精确控制）')

    # 新增增强功能参数
    parser.add_argument('--select', type=str,
                        help='选择表达式（如 1-3,5 或 1-10 -2,4），跳过交互')
    parser.add_argument('--platform', type=str, default='ios',
                        choices=['ios', 'android', 'web'],
                        help='目标平台 (默认: ios)')
    parser.add_argument('--scales', type=str, default='all',
                        help='切图比例 (all 或 2x,3x / mdpi,hdpi 等)')
    parser.add_argument('--formats', type=str, default='png',
                        help='切图格式 (png,webp,svg)，逗号分隔')

    args = parser.parse_args()

    # 解析关键词（支持 --keyword 逗号分隔 和 --keywords 空格分隔）
    keywords = []
    if args.keyword:
        keywords.extend([kw.strip() for kw in args.keyword.split(',') if kw.strip()])
    if args.keywords:
        keywords.extend(args.keywords)

    # 解析 --ids
    design_ids = None
    if args.ids:
        design_ids = [id.strip() for id in args.ids.split(',') if id.strip()]

    # 解析 --scales
    target_scales = None  # None 表示使用默认
    if args.scales and args.scales.lower() != 'all':
        target_scales = [s.strip() for s in args.scales.split(',') if s.strip()]

    # 解析 --formats
    target_formats = [f.strip().lower() for f in args.formats.split(',') if f.strip()]
    if not target_formats:
        target_formats = ['png']

    # 查找项目根目录（向上搜索包含 .claude 文件夹的目录）
    project_root = find_project_root()

    # 加载配置
    try:
        config = load_config(project_root)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)

    # 确定输出目录
    output_base_dir = Path(args.output) if args.output else Path(config.get('output_base_dir', 'docs/lanhu/pages'))

    # --list 模式：只输出设计列表 JSON
    if args.list:
        result = asyncio.run(list_designs(
            url=args.url,
            cookie=config['cookie'],
            keywords=keywords,
            timeout=config.get('timeout', 30)
        ))
        # 输出 JSON 到 stdout
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # 解析 --select 参数
    selection_indices = None
    if args.select:
        # 需要先获取总数
        list_result = asyncio.run(list_designs(
            url=args.url,
            cookie=config['cookie'],
            keywords=keywords,
            timeout=config.get('timeout', 30)
        ))
        total_matched = list_result['matched_count'] if keywords else list_result['total']
        try:
            selection_indices = parse_selection(args.select, total_matched)
        except SelectionParseError as e:
            print(f"❌ Invalid selection: {e}")
            sys.exit(1)

    # 运行导出
    result = asyncio.run(export_lanhu(
        url=args.url,
        output_base_dir=output_base_dir,
        cookie=config['cookie'],
        include_slices=not args.no_slices and config.get('include_slices', True),
        include_preview=not args.no_preview and config.get('include_preview', True),
        timeout=config.get('timeout', 30),
        keywords=keywords,
        design_ids=design_ids,
        # 新增参数
        selection=selection_indices,
        platform=args.platform,
        target_scales=target_scales,
        target_formats=target_formats
    ))

    if not result['success']:
        sys.exit(1)


if __name__ == '__main__':
    main()
