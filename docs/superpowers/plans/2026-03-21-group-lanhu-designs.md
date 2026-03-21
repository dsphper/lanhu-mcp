# group-lanhu-designs 实现计划

## 概述

基于 `docs/superpowers/specs/2026-03-21-group-lanhu-designs-design.md` 设计文档，实现 `group-lanhu-designs` 技能。

## 任务列表

### Task 1: 创建技能目录结构

**目标**: 创建 `skills/group-lanhu-designs/` 目录结构

**文件**:
```
skills/group-lanhu-designs/
├── SKILL.md
├── scripts/
│   ├── __init__.py
│   ├── models.py
│   ├── name_parser.py
│   ├── page_grouper.py
│   ├── slice_merger.py
│   ├── merged_generator.py
│   └── group_designs.py
└── references/
    └── naming-patterns.md
```

**命令**:
```bash
mkdir -p skills/group-lanhu-designs/scripts
mkdir -p skills/group-lanhu-designs/references
touch skills/group-lanhu-designs/scripts/__init__.py
```

**提交**: `feat(group): add directory structure for group-lanhu-designs skill`

---

### Task 2: 实现数据模型 (models.py)

**目标**: 定义核心数据结构

**文件**: `skills/group-lanhu-designs/scripts/models.py`

**依赖**: `analyze-lanhu-design/scripts/models.py` (复用 Layer, Style 等)

**代码**:
```python
"""
group-lanhu-designs 数据模型
"""
from dataclasses import dataclass, field
from pathlib import Path
import re

# 状态关键词列表
STATE_KEYWORDS = [
    # 交互状态
    '展开', '收起', '选中', '未选中', '默认', '悬停', '按下', '聚焦', '禁用',
    # 业务状态
    '商品已兑换', '已兑换', '成功', '失败', '正常', '错误', '加载', '空', '满',
    # 动作状态
    '进行中', '已完成', '待处理'
]

# 组内类型排序顺序
TYPE_ORDER = {'main': 0, 'popup': 1, 'state': 2, 'variant': 3}


@dataclass
class ParsedPageName:
    """解析后的页面名称"""
    original: str                   # 原始名称
    business_order: str | None      # 业务顺序（如 "01"）
    group_name: str                 # 分组名（如 "登录"）
    state: str | None               # 状态（如 "展开"）
    sub_page: str | None            # 子页面名（如 "隐私弹窗"）
    variant: int | None             # 数字变体（如 1）

    @property
    def page_type(self) -> str:
        """组内类型"""
        if self.sub_page:
            return "popup"
        elif self.state:
            return "state"
        elif self.variant is not None:
            return "variant"
        return "main"

    @property
    def group_key(self) -> str:
        """分组键"""
        if self.business_order:
            return f"{self.business_order}_{self.group_name}"
        return self.group_name


@dataclass
class Slice:
    """切图资源"""
    name: str                       # 切图名称（不含后缀）
    path: Path                      # 文件路径
    width: int                      # 宽度（像素）
    height: int                     # 高度（像素）
    page_name: str                  # 来源页面名称
    scale: float = 1.0              # 缩放比例（@1x/@2x/@3x）
    sources: list = field(default_factory=list)  # 所有来源

    @property
    def area(self) -> int:
        """面积（用于尺寸比较）"""
        return self.width * self.height

    @property
    def base_name(self) -> str:
        """基础名称（去除 @2x/@3x 后缀）"""
        return re.sub(r'@\d+x$', '', self.name)


@dataclass
class PageGroup:
    """页面分组"""
    group_key: str                  # 分组键
    business_order: str | None      # 业务顺序
    group_name: str                 # 分组名称
    pages: list[ParsedPageName]     # 包含的页面

    @property
    def main_page(self) -> ParsedPageName | None:
        """获取主页面"""
        for p in self.pages:
            if p.page_type == "main":
                return p
        return self.pages[0] if self.pages else None
```

**测试**:
```bash
cd skills/group-lanhu-designs/scripts
python -c "from models import ParsedPageName, Slice, STATE_KEYWORDS; print('OK')"
```

**提交**: `feat(group): add data models for group-lanhu-designs`

---

### Task 3: 实现命名规则解析器 (name_parser.py)

**目标**: 实现页面名称解析算法

**文件**: `skills/group-lanhu-designs/scripts/name_parser.py`

**代码**:
```python
"""
命名规则解析器 - 解析蓝湖页面名称
"""
import re
import unicodedata
from models import ParsedPageName, STATE_KEYWORDS


def normalize_name(name: str) -> str:
    """规范化页面名称，统一不同类型的破折号"""
    # NFKC 规范化
    name = unicodedata.normalize('NFKC', name)
    # 统一破折号为标准形式
    name = name.replace('–', '-').replace('—', '-')
    return name


def parse_page_name(name: str) -> ParsedPageName:
    """
    解析页面名称，返回结构化信息

    算法步骤:
    1. Unicode 规范化
    2. 提取业务顺序前缀 (R0)
    3. 提取子页面/弹窗 (R3) - 优先！
    4. 提取状态后缀 (R1)
    5. 提取数字后缀 (R2)
    """
    original = name
    name = normalize_name(name)

    # 去除尾部下划线
    name = name.rstrip('_')

    business_order = None
    sub_page = None
    state = None
    variant = None

    # R0: 业务顺序前缀
    match = re.match(r'^(\d+)[_\-\.\s]*(.+)$', name)
    if match:
        business_order = match.group(1)
        name = match.group(2)

    # R3: 子页面/弹窗（优先于 R1/R2）
    match = re.search(r'[_\s]*[-]+[_\s]*(.+)$', name)
    if match:
        sub_page = match.group(1).strip()
        name = name[:match.start()]

    # R1: 状态后缀
    state_pattern = '|'.join(re.escape(kw) for kw in STATE_KEYWORDS)
    match = re.search(rf'[-]({state_pattern})$', name)
    if match:
        state = match.group(1)
        name = name[:match.start()]

    # R2: 数字后缀
    if not sub_page:  # 只有在没有子页面时才处理数字后缀
        match = re.search(r'(\d+)$', name)
        if match:
            variant = int(match.group(1))
            name = name[:match.start()]

    return ParsedPageName(
        original=original,
        business_order=business_order,
        group_name=name.strip(),
        state=state,
        sub_page=sub_page,
        variant=variant
    )
```

**测试**:
```bash
cd skills/group-lanhu-designs/scripts
python -c "
from name_parser import parse_page_name
# 测试业务顺序
assert parse_page_name('01_登录').business_order == '01'
# 测试状态后缀
assert parse_page_name('登录-展开').state == '展开'
# 测试子页面
assert parse_page_name('登录_-_隐私弹窗').sub_page == '隐私弹窗'
# 测试 R3 优先于 R2
assert parse_page_name('识别提示_-_1').page_type == 'popup'
print('All tests passed!')
"
```

**提交**: `feat(group): add name parser for page grouping`

---

### Task 4: 实现页面分组器 (page_grouper.py)

**目标**: 将解析后的页面名称分组

**文件**: `skills/group-lanhu-designs/scripts/page_grouper.py`

**代码**:
```python
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
```

**测试**:
```bash
cd skills/group-lanhu-designs/scripts
python -c "
from page_grouper import group_pages
pages = ['01_登录', '01_登录_-_隐私弹窗', '01_登录-展开', '02_首页']
groups = group_pages(pages)
assert len(groups) == 2
assert groups[0].group_key == '01_登录'
assert len(groups[0].pages) == 3
print('All tests passed!')
"
```

**提交**: `feat(group): add page grouper`

---

### Task 5: 实现切图合并器 (slice_merger.py)

**目标**: 合并同名切图，保留最大尺寸

**文件**: `skills/group-lanhu-designs/scripts/slice_merger.py`

**代码**:
```python
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
    slices = []
    image_extensions = {'.png', '.jpg', '.jpeg', '.svg', '.webp'}

    for page_name in page_names:
        # 查找 slices 目录
        slices_dir = export_dir / 'slices' / page_name
        if not slices_dir.exists():
            continue

        for img_file in slices_dir.rglob('*'):
            if img_file.suffix.lower() not in image_extensions:
                continue

            # 提取尺寸（从文件名或尝试读取）
            width, height = 0, 0
            # 简单处理：从 @2x/@3x 推断
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
```

**测试**:
```bash
cd skills/group-lanhu-designs/scripts
python -c "
from slice_merger import extract_scale, merge_slices
from models import Slice
from pathlib import Path

# 测试缩放比例提取
assert extract_scale('icon@2x') == 2.0
assert extract_scale('icon@3x') == 3.0
assert extract_scale('icon') == 1.0

# 测试合并
slices = [
    Slice('icon', Path('a/icon.png'), 48, 48, '登录'),
    Slice('icon@2x', Path('b/icon@2x.png'), 96, 96, '弹窗'),
]
merged = merge_slices(slices)
assert len(merged) == 1
assert merged[0].area == 9216  # 96*96
print('All tests passed!')
"
```

**提交**: `feat(group): add slice merger`

---

### Task 6: 实现合并文档生成器 (merged_generator.py)

**目标**: 生成合并后的 Markdown 分析文档

**文件**: `skills/group-lanhu-designs/scripts/merged_generator.py`

**代码**:
```python
"""
合并文档生成器 - 生成合并后的 Markdown 分析文档
"""
from pathlib import Path
from models import PageGroup, Slice


class MergedGenerator:
    """合并文档生成器"""

    def __init__(self, framework: str = 'html'):
        self.framework = framework

    def generate(self, group: PageGroup, slices: list[Slice]) -> str:
        """
        生成合并后的分析文档

        Args:
            group: 页面分组
            slices: 合并后的切图列表

        Returns:
            Markdown 文档内容
        """
        sections = [
            self._generate_header(group),
            self._generate_pages_section(group),
            self._generate_slices_section(slices),
        ]
        return '\n\n'.join(sections)

    def _generate_header(self, group: PageGroup) -> str:
        """生成文档头部"""
        page_list = ', '.join(
            f"{p.group_name}({p.page_type})"
            for p in group.pages
        )

        lines = [
            f"# {group.group_key} - 合并分析",
            "",
            "## 业务信息",
            "",
            "| 属性 | 值 |",
            "|------|-----|",
            f"| 业务顺序 | {group.business_order or '-'} |",
            f"| 分组名称 | {group.group_name} |",
            f"| 包含页面 | {page_list} |",
        ]
        return '\n'.join(lines)

    def _generate_pages_section(self, group: PageGroup) -> str:
        """生成页面章节"""
        sections = ["---", "", "## 页面详情", ""]

        for i, page in enumerate(group.pages):
            if page.page_type == "main":
                sections.append(f"### 主页面: {page.group_name}")
            elif page.page_type == "popup":
                sections.append(f"### 弹窗: {page.sub_page}")
            elif page.page_type == "state":
                sections.append(f"### 变体: {page.state} 状态")
            else:
                sections.append(f"### 变体: {page.variant}")

            sections.append("")
            sections.append(f"| 属性 | 值 |")
            sections.append(f"|------|-----|")
            sections.append(f"| 原始名称 | {page.original} |")
            sections.append(f"| 组内类型 | {page.page_type} |")
            if page.state:
                sections.append(f"| 状态 | {page.state} |")
            if page.sub_page:
                sections.append(f"| 子页面 | {page.sub_page} |")
            if page.variant is not None:
                sections.append(f"| 变体序号 | {page.variant} |")
            sections.append("")

        return '\n'.join(sections)

    def _generate_slices_section(self, slices: list[Slice]) -> str:
        """生成切图章节"""
        sections = ["---", "", "## 合并切图索引", ""]

        if not slices:
            sections.append("无切图资源。")
            return '\n'.join(sections)

        sections.extend([
            "| 名称 | 尺寸 | 来源页面 |",
            "|------|------|---------|",
        ])

        for s in slices:
            size = f"{s.width}x{s.height}" if s.width and s.height else "-"
            sections.append(f"| {s.name} | {size} | {s.page_name} |")

        sections.append("")
        sections.append(f"**总计**: {len(slices)} 个切图")

        return '\n'.join(sections)
```

**提交**: `feat(group): add merged document generator`

---

### Task 7: 实现主入口脚本 (group_designs.py)

**目标**: 整合所有模块，提供命令行接口

**文件**: `skills/group-lanhu-designs/scripts/group_designs.py`

**代码**:
```python
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

        print(f"    ✓ 生成: {doc_file}")

    print("-" * 50)
    print(f"完成！输出目录: {output_dir}")
    if not args.no_slices:
        print(f"切图合并: {total_slices} 个")


if __name__ == '__main__':
    main()
```

**提交**: `feat(group): add main entry script for group-lanhu-designs`

---

### Task 8: 创建技能文档 (SKILL.md)

**目标**: 创建技能使用文档

**文件**: `skills/group-lanhu-designs/SKILL.md`

**代码**:
```markdown
---
name: group-lanhu-designs
description: 将蓝湖设计数据中相关联的页面（主页面+弹窗+状态变体）分组并合并分析，生成合并后的布局文档和切图资源。触发词：分组蓝湖设计、合并蓝湖页面、group lanhu、页面归类。
compatibility: Claude Code
---

## 功能

- 自动识别页面命名规则，将相关页面分组
- 支持业务顺序前缀（如 01_、02_）
- 支持状态变体识别（如 -展开、-收起）
- 支持弹窗/子页面识别（如 _–_隐私弹窗）
- 合并同名切图，保留最大尺寸
- 生成合并后的 Markdown 分析文档

## 命名规则

| 规则 | 模式 | 示例 |
|------|------|------|
| 业务顺序 | `数字_名称` | 01_登录 |
| 状态后缀 | `名称-状态` | 登录-展开 |
| 子页面 | `名称_-_子页面` | 登录_-_隐私弹窗 |
| 数字变体 | `名称数字` | 识别提示1 |

## 使用方法

```bash
# 基本用法
/group-lanhu-designs docs/lanhu/pages/MyProject

# 指定框架
/group-lanhu-designs docs/lanhu/pages/MyProject --framework flutter

# 不合并切图
/group-lanhu-designs docs/lanhu/pages/MyProject --no-slices
```

## 输出

```
docs/lanhu/pages/MyProject/
└── grouped/
    ├── 01_登录/
    │   ├── 登录-合并分析.md
    │   └── slices/
    └── 02_首页/
        ├── 首页-合并分析.md
        └── slices/
```
```

**提交**: `feat(group): add SKILL.md documentation`

---

### Task 9: 创建命名模式参考 (naming-patterns.md)

**目标**: 创建命名模式参考文档

**文件**: `skills/group-lanhu-designs/references/naming-patterns.md`

**代码**:
```markdown
# 蓝湖页面命名模式参考

## 推荐命名规范

### 业务顺序前缀

使用两位数字前缀表示页面在业务流程中的顺序：

```
01_启动页
02_登录
03_首页
04_我的
```

### 状态变体

使用 `-状态` 后缀表示同一页面的不同状态：

```
商品提货页-展开
商品提货页-收起
商品提货页-商品已兑换
```

### 弹窗/子页面

使用 `_-_` 分隔符表示弹窗或子页面：

```
登录_-_隐私弹窗
首页_-_搜索弹窗
商品详情_-_规格选择
```

### 数字变体

使用数字后缀表示同一类型的不同版本：

```
识别提示1
识别提示2
识别提示3
```

## 完整示例

```
01_启动页
02_登录
02_登录_-_隐私弹窗
02_登录-加载中
03_首页
03_首页_-_搜索弹窗
04_商品列表
04_商品列表-空状态
04_商品列表-加载中
```

## 避免的命名

- `登录弹窗` - 缺少分隔符，无法识别为弹窗
- `Login_Page` - 混合语言，建议统一使用中文
- `页面-01` - 顺序后缀容易被误识别为状态
```

**提交**: `feat(group): add naming patterns reference`

---

### Task 10: 集成测试

**目标**: 使用真实数据进行集成测试

**命令**:
```bash
cd skills/group-lanhu-designs/scripts
python group_designs.py "E:/xen/code/claude/project/lanhu-mcp/docs/lanhu/pages/DesignProject-da907f83-2026032023"
```

**预期输出**:
```
找到 27 个设计页面
识别到 X 个分组
  分组 "识别提示": 6 个页面
    ✓ 生成: grouped/识别提示/识别提示-合并分析.md
  ...
--------------------------------------------------
完成！输出目录: grouped/
```

**验证**:
1. 检查生成的 `grouped/` 目录结构
2. 打开合并分析文档，验证格式正确
3. 检查切图是否正确合并

**提交**: `test(group): add integration test results`

---

## 完成检查清单

- [ ] Task 1: 目录结构创建
- [ ] Task 2: models.py 实现
- [ ] Task 3: name_parser.py 实现
- [ ] Task 4: page_grouper.py 实现
- [ ] Task 5: slice_merger.py 实现
- [ ] Task 6: merged_generator.py 实现
- [ ] Task 7: group_designs.py 实现
- [ ] Task 8: SKILL.md 创建
- [ ] Task 9: naming-patterns.md 创建
- [ ] Task 10: 集成测试通过
