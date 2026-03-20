# Export Lanhu Skill 实现计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将蓝湖设计数据获取从 MCP Server 改为 Claude Code Skill，支持层级获取（URL → Pages → Page Info → Design Info）

**Architecture:** 创建 `skills/export-lanhu/` Skill 目录，包含 Python 脚本直接调用蓝湖 API，从现有 `lanhu_mcp_server.py` 提取核心 API 逻辑，删除 MCP 相关代码

**Tech Stack:** Python 3.10+, httpx, asyncio

---

## 文件结构

```
skills/export-lanhu/
├── SKILL.md                          # Skill 定义
├── scripts/
│   ├── lanhu_api.py                  # API 封装（从 LanhuExtractor 提取）
│   └── export_lanhu.py               # 主导出脚本
├── references/
│   ├── api-reference.md              # API 接口文档
│   └── output-format.md              # 输出格式说明
└── assets/
    ├── lanhu.config.example.json     # 配置模板
    └── README.template.md            # README 模板
```

---

## Task 1: 创建新分支

**Files:**
- N/A

- [ ] **Step 1: 创建并切换到新分支**

```bash
git checkout -b feature/export-lanhu-skill
```

- [ ] **Step 2: 验证分支创建成功**

Run: `git branch --show-current`
Expected: `feature/export-lanhu-skill`

---

## Task 2: 创建 Skill 目录结构

**Files:**
- Create: `skills/export-lanhu/`
- Create: `skills/export-lanhu/scripts/`
- Create: `skills/export-lanhu/references/`
- Create: `skills/export-lanhu/assets/`

- [ ] **Step 1: 创建目录结构**

```bash
mkdir -p skills/export-lanhu/{scripts,references,assets}
```

- [ ] **Step 2: 验证目录创建**

Run: `ls -la skills/export-lanhu/`
Expected: 显示 scripts/, references/, assets/ 目录

- [ ] **Step 3: 提交**

```bash
git add skills/
git commit -m "chore: create export-lanhu skill directory structure"
```

---

## Task 3: 创建 API 封装模块 (lanhu_api.py)

**Files:**
- Create: `skills/export-lanhu/scripts/lanhu_api.py`

- [ ] **Step 1: 创建 lanhu_api.py 基础结构**

```python
"""
蓝湖 API 封装模块
从 lanhu_mcp_server.py 的 LanhuExtractor 类提取核心 API 逻辑
"""
import httpx
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
from typing import Optional
import json

# 常量定义
BASE_URL = "https://lanhuapp.com"
DDS_BASE_URL = "https://dds.lanhuapp.com"
CHINA_TZ_OFFSET = 8  # 东八区


class LanhuAPI:
    """蓝湖 API 客户端"""

    def __init__(self, cookie: str, timeout: int = 30):
        """
        初始化 API 客户端

        Args:
            cookie: 蓝湖认证 Cookie
            timeout: HTTP 超时秒数
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://lanhuapp.com/web/",
            "Accept": "application/json, text/plain, */*",
            "Cookie": cookie,
            "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "request-from": "web",
        }
        self.client = httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=True)

    async def close(self):
        """关闭客户端连接"""
        await self.client.aclose()

    def parse_url(self, url: str) -> dict:
        """
        解析蓝湖 URL，提取参数

        Args:
            url: 蓝湖 URL 或参数字符串

        Returns:
            包含 team_id, project_id, doc_id 的字典
        """
        if url.startswith('http'):
            parsed = urlparse(url)
            fragment = parsed.fragment
            if not fragment:
                raise ValueError("Invalid Lanhu URL: missing fragment part")
            if '?' in fragment:
                url = fragment.split('?', 1)[1]
            else:
                url = fragment

        if url.startswith('?'):
            url = url[1:]

        params = {}
        for part in url.split('&'):
            if '=' in part:
                key, value = part.split('=', 1)
                params[key] = value

        team_id = params.get('tid')
        project_id = params.get('pid')
        doc_id = params.get('docId') or params.get('image_id')

        if not project_id:
            raise ValueError("URL parsing failed: missing required param pid")
        if not team_id:
            raise ValueError("URL parsing failed: missing required param tid")

        return {
            'team_id': team_id,
            'project_id': project_id,
            'doc_id': doc_id
        }
```

- [ ] **Step 2: 添加 get_pages_list 方法**

```python
    async def get_document_info(self, project_id: str, doc_id: str) -> dict:
        """获取文档信息"""
        api_url = f"{BASE_URL}/api/project/image"
        params = {'pid': project_id, 'image_id': doc_id}

        response = await self.client.get(api_url, params=params)
        response.raise_for_status()
        data = response.json()

        code = data.get('code')
        success = (code == 0 or code == '0' or code == '00000')
        if not success:
            raise Exception(f"API Error: {data.get('msg')} (code={code})")

        return data.get('data') or data.get('result', {})

    async def get_pages_list(self, url: str) -> dict:
        """
        获取文档的所有页面列表

        Args:
            url: 蓝湖 URL

        Returns:
            包含 pages 列表的字典
        """
        params = self.parse_url(url)
        doc_info = await self.get_document_info(params['project_id'], params['doc_id'])

        versions = doc_info.get('versions', [])
        if not versions:
            raise Exception("Document version info not found")

        latest_version = versions[0]
        json_url = latest_version.get('json_url')
        if not json_url:
            raise Exception("Mapping JSON URL not found")

        response = await self.client.get(json_url)
        response.raise_for_status()
        project_mapping = response.json()

        # 从 sitemap 获取页面列表
        sitemap = project_mapping.get('sitemap', {})
        root_nodes = sitemap.get('rootNodes', [])

        def extract_pages(nodes, pages_list, level=0):
            for node in nodes:
                page_name = node.get('pageName', '')
                url_path = node.get('url', '')
                node_id = node.get('id', '')

                if page_name and url_path:
                    pages_list.append({
                        'name': page_name,
                        'filename': url_path,
                        'id': node_id,
                        'level': level
                    })

                children = node.get('children', [])
                if children:
                    extract_pages(children, pages_list, level + 1)

        pages_list = []
        extract_pages(root_nodes, pages_list)

        return {
            'document_id': params['doc_id'],
            'document_name': doc_info.get('name', 'Unknown'),
            'project_id': params['project_id'],
            'team_id': params['team_id'],
            'version_id': latest_version.get('version_id', ''),
            'total_pages': len(pages_list),
            'pages': pages_list
        }
```

- [ ] **Step 3: 添加设计数据获取方法**

```python
    async def get_design_list(self, team_id: str, project_id: str) -> list:
        """获取设计图列表"""
        api_url = f"{BASE_URL}/api/project/images"
        params = {'project_id': project_id}

        response = await self.client.get(api_url, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get('code') != '00000':
            raise Exception(f"API Error: {data.get('msg')}")

        return data.get('result', {}).get('list', [])

    async def get_design_schema_json(self, image_id: str, team_id: str, project_id: str) -> dict:
        """获取设计 Schema JSON"""
        api_url = f"{BASE_URL}/api/service_model/image_layer_tree"
        params = {
            'image_id': image_id,
            'team_id': team_id,
            'project_id': project_id
        }

        response = await self.client.get(api_url, params=params)
        response.raise_for_status()
        return response.json()

    async def get_sketch_json(self, image_id: str, team_id: str, project_id: str) -> dict:
        """获取 Sketch JSON"""
        api_url = f"{DDS_BASE_URL}/api/service_model/sketch"
        params = {
            'image_id': image_id,
            'team_id': team_id,
            'project_id': project_id
        }

        response = await self.client.get(api_url, params=params)
        response.raise_for_status()
        return response.json()

    async def get_slices_info(self, image_id: str, team_id: str, project_id: str) -> list:
        """获取切图信息"""
        api_url = f"{BASE_URL}/api/project/image_slice_categories"
        params = {
            'image_id': image_id,
            'team_id': team_id,
            'project_id': project_id
        }

        response = await self.client.get(api_url, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get('code') != '00000':
            return []

        slices = []
        for category in data.get('result', {}).get('list', []):
            for item in category.get('sliceList', []):
                slices.append({
                    'name': item.get('name', ''),
                    'url': item.get('url', ''),
                    'width': item.get('width', 0),
                    'height': item.get('height', 0),
                    'scale': item.get('scale', '1x')
                })
        return slices
```

- [ ] **Step 4: 提交**

```bash
git add skills/export-lanhu/scripts/lanhu_api.py
git commit -m "feat: add lanhu_api.py module with core API methods"
```

---

## Task 4: 创建主导出脚本 (export_lanhu.py)

**Files:**
- Create: `skills/export-lanhu/scripts/export_lanhu.py`

- [ ] **Step 1: 创建导出脚本基础结构**

```python
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
```

- [ ] **Step 2: 添加下载函数**

```python
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
```

- [ ] **Step 3: 添加主导出函数**

```python
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


def generate_readme(output_dir: Path, meta: dict, pages: list, designs: list):
    """生成 README.md"""
    content = f"""# {meta['project_name']} - 蓝湖设计数据

## 基本信息

- **项目名称**: {meta['project_name']}
- **数据来源**: {meta['source_url']}
- **导出时间**: {meta['export_time']}
- **版本 ID**: {meta['version_id'][:8]}...

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
```

- [ ] **Step 4: 添加主函数**

```python
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
```

- [ ] **Step 5: 提交**

```bash
git add skills/export-lanhu/scripts/export_lanhu.py
git commit -m "feat: add export_lanhu.py main export script"
```

---

## Task 5: 创建 SKILL.md

**Files:**
- Create: `skills/export-lanhu/SKILL.md`

- [ ] **Step 1: 创建 SKILL.md**

```markdown
---
name: export-lanhu
description: |
  导出蓝湖设计数据到本地项目。

  触发场景：导出蓝湖、蓝湖设计、下载切图、同步设计稿、拉取设计数据、
  UI设计导出、设计数据保存、蓝湖数据导出、设计稿同步。

  当用户提到蓝湖、设计稿、切图、UI设计导出时，使用此 Skill。
compatibility:
  tools: [Bash, Read, Write]
  dependencies: [httpx]
---

## 使用方式

```bash
/export-lanhu <URL> [--output <目录>] [--no-slices] [--no-preview]
```

## 参数

| 参数 | 说明 |
|------|------|
| `URL` | 蓝湖项目链接（必填） |
| `--output` | 自定义输出目录 |
| `--no-slices` | 跳过切图下载 |
| `--no-preview` | 跳过预览图下载 |

## 前置条件

1. 在项目根目录创建 `.claude/lanhu.config.json` 配置文件
2. 配置文件中必须包含 `cookie` 字段

## 配置文件示例

```json
{
  "cookie": "你的蓝湖 Cookie",
  "output_base_dir": "docs/lanhu/pages",
  "include_slices": true,
  "include_preview": true,
  "timeout": 30
}
```

## 执行步骤

1. 读取配置文件 `.claude/lanhu.config.json`
2. 解析蓝湖 URL
3. 获取页面列表（Pages）
4. 获取每个页面的详情
5. 获取设计图列表（Designs）
6. 下载设计数据：Schema JSON + Sketch JSON + 预览图
7. 下载切图资源
8. 生成 README.md 和 meta.json

## 输出

数据保存到 `docs/lanhu/pages/{项目名}-{yyyyMMddHH}/`

```
{项目名}-{yyyyMMddHH}/
├── pages/           # 页面数据
├── designs/         # 设计图数据
├── slices/          # 切图资源
├── meta.json        # 元数据
└── README.md        # 说明文档
```

## 执行命令

执行 Python 脚本：

```bash
cd skills/export-lanhu/scripts
python export_lanhu.py "<URL>"
```
```

- [ ] **Step 2: 提交**

```bash
git add skills/export-lanhu/SKILL.md
git commit -m "feat: add SKILL.md definition"
```

---

## Task 6: 创建资源文件

**Files:**
- Create: `skills/export-lanhu/assets/lanhu.config.example.json`
- Create: `skills/export-lanhu/assets/README.template.md`

- [ ] **Step 1: 创建配置模板**

```json
{
  "cookie": "你的蓝湖 Cookie（必填，从浏览器开发者工具获取）",
  "output_base_dir": "docs/lanhu/pages",
  "include_slices": true,
  "include_preview": true,
  "download_concurrent": 5,
  "timeout": 30
}
```

- [ ] **Step 2: 创建参考文档**

创建 `references/api-reference.md`：

```markdown
# 蓝湖 API 参考

## 认证

所有 API 请求需要在 Header 中携带 Cookie。

## 核心 API

### 获取页面列表

```
GET /api/project/image?pid={project_id}&image_id={doc_id}
```

### 获取设计列表

```
GET /api/project/images?project_id={project_id}
```

### 获取设计 Schema

```
GET /api/service_model/image_layer_tree?image_id={image_id}&team_id={team_id}&project_id={project_id}
```

### 获取 Sketch JSON

```
GET https://dds.lanhuapp.com/api/service_model/sketch?image_id={image_id}&team_id={team_id}&project_id={project_id}
```

### 获取切图信息

```
GET /api/project/image_slice_categories?image_id={image_id}&team_id={team_id}&project_id={project_id}
```
```

- [ ] **Step 3: 创建输出格式文档**

创建 `references/output-format.md`：

```markdown
# 输出格式说明

## 目录结构

```
docs/lanhu/pages/{项目名}-{yyyyMMddHH}/
├── README.md
├── meta.json
├── pages/
│   └── {页面名}/
│       └── page.json
├── designs/
│   └── {设计名}/
│       ├── schema.json
│       ├── sketch.json
│       └── preview.png
└── slices/
    └── {切图名}.png
```

## meta.json 格式

```json
{
  "source_url": "https://lanhuapp.com/...",
  "project_name": "项目名称",
  "project_id": "xxx",
  "export_time": "2026-03-20T10:30:00",
  "version_id": "abc123",
  "page_count": 30,
  "design_count": 80,
  "slice_count": 200
}
```
```

- [ ] **Step 4: 提交**

```bash
git add skills/export-lanhu/assets/ skills/export-lanhu/references/
git commit -m "feat: add assets and references"
```

---

## Task 7: 删除 MCP Server 相关文件

**Files:**
- Delete: `lanhu_mcp_server.py`
- Delete: `Dockerfile`
- Delete: `docker-compose.yml`
- Delete: `.env.example`
- Delete: `.dockerignore`

- [ ] **Step 1: 删除文件**

```bash
rm lanhu_mcp_server.py Dockerfile docker-compose.yml .env.example .dockerignore
```

- [ ] **Step 2: 验证删除**

Run: `ls lanhu_mcp_server.py 2>&1`
Expected: `No such file or directory`

- [ ] **Step 3: 提交**

```bash
git add -A
git commit -m "refactor: remove MCP server, migrate to skill-based approach"
```

---

## Task 8: 更新 requirements.txt

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: 更新依赖**

```txt
httpx>=0.27.0
beautifulsoup4>=4.12.0
lxml>=5.0.0
python-dotenv>=1.0.0
```

- [ ] **Step 2: 提交**

```bash
git add requirements.txt
git commit -m "chore: update requirements.txt, remove MCP dependencies"
```

---

## Task 9: 更新 README.md

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 更新使用说明**

将 MCP Server 相关说明替换为 Skill 使用说明。

- [ ] **Step 2: 提交**

```bash
git add README.md
git commit -m "docs: update README for skill-based approach"
```

---

## Task 10: 测试验证

**Files:**
- N/A

- [ ] **Step 1: 创建测试配置**

在项目根目录创建 `.claude/lanhu.config.json`（使用真实 Cookie）

- [ ] **Step 2: 运行导出脚本**

```bash
cd skills/export-lanhu/scripts
python export_lanhu.py "https://lanhuapp.com/web/#/item/project/product?tid=xxx&pid=xxx&docId=xxx"
```

- [ ] **Step 3: 验证输出**

检查 `docs/lanhu/pages/{项目名}-{日期}/` 目录结构和内容

---

## 验收标准

- [ ] 执行 `/export-lanhu <URL>` 能成功导出数据
- [ ] 输出目录结构符合设计（pages/、designs/、slices/）
- [ ] README.md 包含项目名称和完整信息
- [ ] 配置从 `.claude/lanhu.config.json` 正确读取
- [ ] 原有 MCP Server 代码已删除
- [ ] 所有测试通过
