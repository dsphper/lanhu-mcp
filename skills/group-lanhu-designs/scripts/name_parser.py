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
    # 匹配 _-_ 或 -_-_ 等模式，分隔符为横线+下划线组合
    match = re.search(r'[-_]+-[-_]+(.+)$', name)
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
