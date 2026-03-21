"""
选择表达式解析器

语法:
    1,3,5      - 选择第 1、3、5 个
    1-5        - 选择第 1 到 5 个
    1-5,8,10   - 范围和单选组合
    1-5 -2,4   - 范围选择后排除 2 和 4
    *          - 全选
    ^2,4       - 全选后排除 2 和 4
"""
import re
from typing import List


class SelectionParseError(Exception):
    """选择表达式解析错误"""
    pass


def _parse_numbers(expr: str, total: int) -> set:
    """
    解析数字表达式（不含排除）

    Args:
        expr: 表达式如 "1-5,8,10"
        total: 总数量

    Returns:
        选中的索引集合（0-based）
    """
    selected = set()

    if not expr.strip():
        return selected

    parts = expr.split(',')
    for part in parts:
        part = part.strip()
        if not part:
            continue

        if '-' in part:
            # 范围表达式
            match = re.match(r'^(\d+)\s*-\s*(\d+)$', part)
            if not match:
                raise SelectionParseError(f"Invalid range: {part}")
            start, end = int(match.group(1)), int(match.group(2))
            if start > end:
                raise SelectionParseError(f"Invalid range: {start} > {end}")
            if end > total:
                raise SelectionParseError(f"Index {end} out of range (max: {total})")
            selected.update(range(start - 1, end))  # 转为 0-based
        else:
            # 单个数字
            try:
                num = int(part)
            except ValueError:
                raise SelectionParseError(f"Invalid number: {part}")
            if num < 1 or num > total:
                raise SelectionParseError(f"Index {num} out of range (1-{total})")
            selected.add(num - 1)  # 转为 0-based

    return selected


def parse_selection(expression: str, total_count: int) -> List[int]:
    """
    解析选择表达式

    Args:
        expression: 选择表达式
        total_count: 总数量

    Returns:
        选中的索引列表（0-based，已排序）

    Raises:
        SelectionParseError: 表达式无效

    Examples:
        "1,3,5" → [0, 2, 4]
        "1-5" → [0, 1, 2, 3, 4]
        "1-5 -2,4" → [0, 2]
        "*" → [0, 1, ..., total_count-1]
        "^2,4" → 全选后排除
    """
    if total_count <= 0:
        return []

    expression = expression.strip()

    # 空字符串或 * 表示全选
    if not expression or expression == '*':
        return list(range(total_count))

    # 检查排除模式（以 ^ 开头）
    if expression.startswith('^'):
        exclude_expr = expression[1:].strip()
        all_indices = set(range(total_count))
        exclude_set = _parse_numbers(exclude_expr, total_count)
        result = all_indices - exclude_set
        return sorted(result)

    # 检查是否有排除部分（空格后的 -）
    # 策略：找到所有可能的 "空白 -" 位置，从右向左尝试，使用第一个能成功解析的

    # 收集所有可能的排除标记位置
    possible_positions = []
    for match in re.finditer(r'\s+-\s*(\d)', expression):
        possible_positions.append(match.start())

    # 从右向左尝试每个位置
    for pos in reversed(possible_positions):
        match = re.match(r'\s+-\s*(\d.*)$', expression[pos:])
        if match:
            select_expr = expression[:pos].rstrip()
            exclude_expr = match.group(1)  # 从捕获的数字开始到末尾
            try:
                select_set = _parse_numbers(select_expr, total_count)
                exclude_set = _parse_numbers(exclude_expr, total_count)
                result = select_set - exclude_set
                return sorted(result)
            except SelectionParseError:
                # 这个位置解析失败，尝试下一个
                continue

    # 纯选择模式
    select_set = _parse_numbers(expression, total_count)
    return sorted(select_set)
