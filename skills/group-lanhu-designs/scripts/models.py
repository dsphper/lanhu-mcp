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
