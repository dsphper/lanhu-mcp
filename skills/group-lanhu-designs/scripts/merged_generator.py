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
