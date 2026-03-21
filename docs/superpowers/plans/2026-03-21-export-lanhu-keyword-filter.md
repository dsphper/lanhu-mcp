# Export Lanhu 关键词过滤功能 实现计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 export-lanhu skill 添加关键词过滤功能，支持两阶段交互式导出

**Architecture:** 在现有 Python 脚本基础上添加 `--list`、`--keyword`、`--keywords`、`--ids` 参数，重写 SKILL.md 实现智能解析和交互流程

**Tech Stack:** Python 3.10+, argparse, httpx, asyncio

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `skills/export-lanhu/scripts/export_lanhu.py` | 修改 | 添加参数解析、关键词过滤、--list 模式 |
| `skills/export-lanhu/SKILL.md` | 重写 | 两阶段交互流程、智能解析指令 |

---

## Task 1: 添加关键词过滤函数

**Files:**
- Modify: `skills/export-lanhu/scripts/export_lanhu.py:43-51` (在 `sanitize_filename` 函数后添加)

- [ ] **Step 1: 添加 filter_designs_by_keywords 函数**

在 `sanitize_filename` 函数后添加：

```python
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
```

- [ ] **Step 2: 提交**

```bash
git add skills/export-lanhu/scripts/export_lanhu.py
git commit -m "feat(export): add filter_designs_by_keywords function"
```

---

## Task 2: 添加 --list 模式输出函数

**Files:**
- Modify: `skills/export-lanhu/scripts/export_lanhu.py` (在 `filter_designs_by_keywords` 后添加)

- [ ] **Step 1: 添加 output_design_list 函数**

```python
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
```

- [ ] **Step 2: 提交**

```bash
git add skills/export-lanhu/scripts/export_lanhu.py
git commit -m "feat(export): add output_design_list function for --list mode"
```

---

## Task 3: 添加新参数解析

**Files:**
- Modify: `skills/export-lanhu/scripts/export_lanhu.py:447-454` (main 函数中的 argparse 部分)

- [ ] **Step 1: 添加新参数定义**

找到 `parser.add_argument('--no-preview', ...)` 行，在其后添加：

```python
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
```

- [ ] **Step 2: 提交**

```bash
git add skills/export-lanhu/scripts/export_lanhu.py
git commit -m "feat(export): add --list, --keyword, --keywords, --ids arguments"
```

---

## Task 4: 添加关键词解析逻辑

**Files:**
- Modify: `skills/export-lanhu/scripts/export_lanhu.py` (在 main 函数中，参数解析后)

- [ ] **Step 1: 在 main 函数中添加关键词解析逻辑**

找到 `args = parser.parse_args()` 行，在其后添加：

```python
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
```

- [ ] **Step 2: 提交**

```bash
git add skills/export-lanhu/scripts/export_lanhu.py
git commit -m "feat(export): add keyword and ids parsing logic"
```

---

## Task 5: 添加 list_designs 异步函数

**Files:**
- Modify: `skills/export-lanhu/scripts/export_lanhu.py` (在 `export_lanhu` 函数前添加)

- [ ] **Step 1: 添加 list_designs 函数**

在 `export_lanhu` 函数前添加：

```python
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
```

- [ ] **Step 2: 提交**

```bash
git add skills/export-lanhu/scripts/export_lanhu.py
git commit -m "feat(export): add list_designs async function"
```

---

## Task 6: 修改 export_lanhu 函数支持过滤

**Files:**
- Modify: `skills/export-lanhu/scripts/export_lanhu.py:269-276` (export_lanhu 函数签名)

- [ ] **Step 1: 修改 export_lanhu 函数签名**

将：
```python
async def export_lanhu(
    url: str,
    output_base_dir: Path,
    cookie: str,
    include_slices: bool = True,
    include_preview: bool = True,
    timeout: int = 30
) -> dict:
```

改为：
```python
async def export_lanhu(
    url: str,
    output_base_dir: Path,
    cookie: str,
    include_slices: bool = True,
    include_preview: bool = True,
    timeout: int = 30,
    keywords: list = None,
    design_ids: list = None
) -> dict:
```

- [ ] **Step 2: 提交**

```bash
git add skills/export-lanhu/scripts/export_lanhu.py
git commit -m "feat(export): add keywords and design_ids params to export_lanhu"
```

---

## Task 7: 在 export_lanhu 中添加过滤逻辑

**Files:**
- Modify: `skills/export-lanhu/scripts/export_lanhu.py:333-350` (获取设计列表后的处理)

- [ ] **Step 1: 在获取设计列表后添加过滤逻辑**

找到：
```python
        # 4. 获取设计列表
        print("🎨 Fetching designs list...")
        designs = await api.get_design_list(team_id, project_id)

        # 5. 下载设计数据
```

改为：
```python
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
            designs, _ = filter_designs_by_keywords(designs, keywords)
            print(f"🔍 Filtered by keywords: {len(designs)} designs")

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

        # 5. 下载设计数据
```

- [ ] **Step 2: 提交**

```bash
git add skills/export-lanhu/scripts/export_lanhu.py
git commit -m "feat(export): add design filtering logic in export_lanhu"
```

---

## Task 8: 修改 main 函数处理 --list 和新参数

**Files:**
- Modify: `skills/export-lanhu/scripts/export_lanhu.py:469-481` (main 函数的执行部分)

- [ ] **Step 1: 修改 main 函数执行逻辑**

找到：
```python
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
```

改为：
```python
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

    # 运行导出
    result = asyncio.run(export_lanhu(
        url=args.url,
        output_base_dir=output_base_dir,
        cookie=config['cookie'],
        include_slices=not args.no_slices and config.get('include_slices', True),
        include_preview=not args.no_preview and config.get('include_preview', True),
        timeout=config.get('timeout', 30),
        keywords=keywords,
        design_ids=design_ids
    ))

    if not result['success']:
        sys.exit(1)
```

- [ ] **Step 2: 提交**

```bash
git add skills/export-lanhu/scripts/export_lanhu.py
git commit -m "feat(export): handle --list mode and new filter params in main"
```

---

## Task 9: 重写 SKILL.md

**Files:**
- Rewrite: `skills/export-lanhu/SKILL.md`

- [ ] **Step 1: 重写完整的 SKILL.md**

```markdown
---
name: export-lanhu
description: |
  导出蓝湖设计数据到本地项目（支持关键词过滤）。

  触发场景：导出蓝湖、蓝湖设计、下载切图、同步设计稿、拉取设计数据、
  UI设计导出、设计数据保存、蓝湖数据导出、设计稿同步、按关键词导出设计。

  当用户提到蓝湖、设计稿、切图、UI设计导出时，使用此 Skill。
compatibility:
  tools: [Bash, Read, Write]
  dependencies: [httpx]
---

## 使用方式

用户可以通过自然语言描述导出需求：

- "导出蓝湖 <URL> 和登录相关的页面数据"
- "导出蓝湖 <URL> 的全部设计"
- "导出蓝湖 <URL> 中登录、注册相关的设计"

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
  "timeout": 300
}
```

## 获取 Cookie 方法

1. 登录蓝湖网页版 (https://lanhuapp.com)
2. 按 F12 打开开发者工具
3. 切换到 Network 标签
4. 刷新页面，找到任意请求
5. 在 Headers 中找到 Cookie 字段
6. 复制完整的 Cookie 值

## 执行流程

### 步骤 1：解析用户输入

1. **提取蓝湖 URL**
   - 匹配 `lanhuapp.com` 开头的链接
   - 支持 `http://` 和 `https://`

2. **提取关键词**
   - 从用户描述中识别业务词（如"登录"、"注册"、"支付"）
   - 常见关键词模式：
     - "和 X 相关的"
     - "X 相关的页面"
     - "包含 X 的设计"
     - "X 相关"
   - 如果用户说"全部"、"所有"或未指定关键词，则无关键词

3. **多关键词处理**
   - 多个关键词用逗号连接传递给脚本

### 步骤 2：获取设计列表（预览）

执行命令获取设计列表：

```bash
cd skills/export-lanhu/scripts
python export_lanhu.py "<URL>" --keyword <关键词> --list
```

无关键词时：

```bash
python export_lanhu.py "<URL>" --list
```

**输出 JSON 格式：**

```json
{
  "source_url": "https://lanhuapp.com/...",
  "project_name": "电商APP设计",
  "project_id": "xxx",
  "total": 28,
  "matched_count": 5,
  "matched": [
    {"id": "abc", "name": "登录页"},
    {"id": "def", "name": "登录页-手机号"}
  ],
  "unmatched_count": 23,
  "unmatched": [
    {"id": "xxx", "name": "商品详情"}
  ]
}
```

### 步骤 3：展示结果并确认

解析 JSON 输出，展示给用户：

```
🎯 匹配"登录"的设计图 (5/28)：

  ✅ 登录页
  ✅ 登录页-手机号
  ✅ 登录页-验证码
  ✅ 登录成功
  ✅ 忘记登录密码

📋 其他设计（23 个）：商品详情、支付成功、我的...

是否导出这 5 个设计？
```

**交互选项：**
- 用户确认 → 执行导出
- 用户要求调整 → 重新过滤或使用 `--ids` 精确指定
- 用户说"全部导出" → 不带关键词导出所有设计

### 步骤 4：执行导出

用户确认后执行：

```bash
python export_lanhu.py "<URL>" --keyword <关键词>
```

精确指定 ID：

```bash
python export_lanhu.py "<URL>" --ids <id1>,<id2>,<id3>
```

导出全部（无过滤）：

```bash
python export_lanhu.py "<URL>"
```

## 输出

数据保存到 `docs/lanhu/pages/{项目名}-{yyyyMMddHH}/`

```
{项目名}-{yyyyMMddHH}/
├── designs/         # 设计图数据
│   └── {设计名}/
│       ├── schema.json
│       ├── sketch.json
│       └── preview.png
├── slices/          # 切图资源
│   └── {切图名}.png
├── meta.json        # 元数据
└── README.md        # 说明文档
```

## 关键词匹配规则

- 匹配方式：包含匹配（设计名包含关键词即匹配）
- 多关键词：OR 逻辑（匹配任意一个即可）
- 大小写：不区分

## 可选参数

| 参数 | 说明 |
|------|------|
| `--output, -o` | 自定义输出目录 |
| `--no-slices` | 跳过切图下载 |
| `--no-preview` | 跳过预览图下载 |

## 示例场景

**场景 1：导出登录相关设计**
```
用户：导出蓝湖 https://lanhuapp.com/... 和登录相关的页面数据
Claude：执行预览 → 展示匹配结果 → 用户确认 → 执行导出
```

**场景 2：导出全部设计**
```
用户：导出蓝湖 https://lanhuapp.com/... 的所有设计
Claude：直接执行导出（无过滤）
```

**场景 3：精确指定设计**
```
用户：导出蓝湖 https://lanhuapp.com/... 只要登录页和注册页
Claude：预览 → 用户确认后用 --ids 精确导出
```
```

- [ ] **Step 2: 提交**

```bash
git add skills/export-lanhu/SKILL.md
git commit -m "docs(skill): rewrite SKILL.md with two-phase interactive flow"
```

---

## Task 10: 验证功能

- [ ] **Step 1: 验证 --list 输出格式**

运行命令验证 JSON 输出：

```bash
cd skills/export-lanhu/scripts
python export_lanhu.py "<测试URL>" --list
```

预期：输出有效的 JSON，包含 `matched`、`unmatched` 等字段

- [ ] **Step 2: 验证关键词过滤**

```bash
python export_lanhu.py "<测试URL>" --keyword 登录 --list
```

预期：`matched` 列表只包含名称含"登录"的设计

- [ ] **Step 3: 验证导出功能**

```bash
python export_lanhu.py "<测试URL>" --keyword 登录 --no-slices
```

预期：只下载匹配的设计数据

---

## 验收标准

- [ ] `--list` 模式输出有效 JSON
- [ ] `--keyword` 过滤功能正常（单个/多个关键词）
- [ ] `--ids` 精确导出功能正常
- [ ] 无关键词时导出全部（向后兼容）
- [ ] SKILL.md 文档完整，指导 Claude 进行两阶段交互
