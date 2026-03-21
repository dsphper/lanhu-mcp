# test_selection_parser.py
import pytest
from selection_parser import parse_selection, SelectionParseError


class TestParseSelection:
    """选择表达式解析测试"""

    def test_single_number(self):
        """单选：1 → [0]"""
        assert parse_selection("1", 10) == [0]

    def test_multiple_numbers(self):
        """多选：1,3,5 → [0, 2, 4]"""
        assert parse_selection("1,3,5", 10) == [0, 2, 4]

    def test_range(self):
        """范围：1-5 → [0, 1, 2, 3, 4]"""
        assert parse_selection("1-5", 10) == [0, 1, 2, 3, 4]

    def test_range_and_numbers(self):
        """范围+单选：1-3,5,7 → [0, 1, 2, 4, 6]"""
        assert parse_selection("1-3,5,7", 10) == [0, 1, 2, 4, 6]

    def test_exclude(self):
        """排除：1-5 -2,4 → [0, 2, 4]"""
        assert parse_selection("1-5 -2,4", 10) == [0, 2, 4]

    def test_select_all(self):
        """全选：* → [0..9]"""
        assert parse_selection("*", 10) == list(range(10))

    def test_exclude_all(self):
        """全选后排除：^2,4 → [0, 2, 4, 5, 6, 7, 8, 9]"""
        assert parse_selection("^2,4", 10) == [0, 2, 4, 5, 6, 7, 8, 9]

    def test_exclude_range(self):
        """排除范围：1-10 -3-5 → [0, 1, 5, 6, 7, 8, 9]"""
        assert parse_selection("1-10 -3-5", 10) == [0, 1, 5, 6, 7, 8, 9]

    def test_out_of_range(self):
        """超出范围抛出错误"""
        with pytest.raises(SelectionParseError):
            parse_selection("1-20", 10)

    def test_invalid_syntax(self):
        """无效语法抛出错误"""
        with pytest.raises(SelectionParseError):
            parse_selection("1--5", 10)

    def test_empty_string(self):
        """空字符串返回全选"""
        assert parse_selection("", 10) == list(range(10))

    def test_whitespace_handling(self):
        """空格处理"""
        assert parse_selection("  1 , 3 , 5  ", 10) == [0, 2, 4]
        assert parse_selection("1 - 5  -  2 , 4", 10) == [0, 2, 4]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
