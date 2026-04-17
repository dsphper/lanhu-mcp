#!/usr/bin/env python3
"""
蓝湖Axure文档提取MCP服务器
使用FastMCP实现
"""
import asyncio
import os
import re
import base64
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Annotated, Optional, Union, List, Any

# 加载 .env 文件中的环境变量（必须在其他导入之前）
# 注意：在 Docker 容器中，环境变量通常已由 docker-compose 通过 env_file 设置
# load_dotenv() 默认不会覆盖已存在的环境变量，所以与 Docker Compose 兼容
try:
    from dotenv import load_dotenv
    # 从项目根目录加载 .env 文件（如果存在）
    # override=False 确保不会覆盖已存在的环境变量（如 Docker Compose 设置的）
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path, override=False)
    else:
        # 如果 .env 文件不存在，尝试从当前目录加载（用于本地开发）
        load_dotenv(override=False)
except ImportError:
    # 如果 python-dotenv 未安装，跳过加载（使用系统环境变量）
    pass

# 东八区时区（北京时间）
CHINA_TZ = timezone(timedelta(hours=8))
from urllib.parse import urlparse

# 元数据缓存配置（基于版本号的永久缓存）
_metadata_cache = {}  # {cache_key: {'data': {...}, 'version_id': str}}

import httpx
from fastmcp import Context
from bs4 import BeautifulSoup
from fastmcp import FastMCP
from fastmcp.utilities.types import Image
from playwright.async_api import async_playwright

# 创建FastMCP服务器
mcp = FastMCP("Lanhu Axure Extractor")

# 全局配置
DEFAULT_COOKIE = "your_lanhu_cookie_here"  # 请替换为你的蓝湖Cookie，从浏览器开发者工具中获取

# 从环境变量读取Cookie，如果没有则使用默认值
COOKIE = os.getenv("LANHU_COOKIE", DEFAULT_COOKIE)

BASE_URL = "https://lanhuapp.com"
DDS_BASE_URL = "https://dds.lanhuapp.com"
CDN_URL = "https://axure-file.lanhuapp.com"
DDS_COOKIE = os.getenv("DDS_COOKIE", COOKIE)

# 飞书机器人Webhook配置（支持环境变量）
DEFAULT_FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook-key-here"
FEISHU_WEBHOOK_URL = os.getenv("FEISHU_WEBHOOK_URL", DEFAULT_FEISHU_WEBHOOK)

# 数据存储目录
DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# HTTP 请求超时时间（秒）
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "30"))

# 浏览器视口尺寸（影响页面初始渲染，不影响全页截图）
# 注意：截图使用 full_page=True，会自动截取完整页面，不受此限制
VIEWPORT_WIDTH = int(os.getenv("VIEWPORT_WIDTH", "1920"))
VIEWPORT_HEIGHT = int(os.getenv("VIEWPORT_HEIGHT", "1080"))

# 调试模式
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# 角色枚举（用于识别用户身份）
VALID_ROLES = ["后端", "前端", "客户端", "开发", "运维", "产品", "项目经理"]

# ⚠️ @提醒只允许具体人名，禁止使用角色
# 示例人名列表，请根据你的团队成员修改
MENTION_ROLES = [
    "张三", "李四", "王五", "赵六", "钱七", "孙八",
    "周九", "吴十", "郑十一", "冯十二", "陈十三", "褚十四",
    "卫十五", "蒋十六", "沈十七", "韩十八", "杨十九", "朱二十"
]

# 飞书用户ID映射
# 示例映射，请替换为你团队成员的实际飞书用户ID
# 飞书用户ID可以通过飞书开放平台获取
FEISHU_USER_ID_MAP = {
    '张三': '0000000000000000001',
    '李四': '0000000000000000002',
    '王五': '0000000000000000003',
    '赵六': '0000000000000000004',
    '钱七': '0000000000000000005',
    '孙八': '0000000000000000006',
    '周九': '0000000000000000007',
    '吴十': '0000000000000000008',
    '郑十一': '0000000000000000009',
    '冯十二': '0000000000000000010',
    '陈十三': '0000000000000000011',
    '褚十四': '0000000000000000012',
    '卫十五': '0000000000000000013',
    '蒋十六': '0000000000000000014',
    '沈十七': '0000000000000000015',
    '韩十八': '0000000000000000016',
    '杨十九': '0000000000000000017',
    '朱二十': '0000000000000000018',
}

# 角色映射规则（按优先级排序，越具体的越靠前）
ROLE_MAPPING_RULES = [
    # 后端相关
    (["后端", "backend", "服务端", "server", "java", "php", "python", "go", "golang", "node", "nodejs", ".net", "c#"], "后端"),
    # 前端相关
    (["前端", "frontend", "h5", "web", "vue", "react", "angular", "javascript", "js", "ts", "typescript", "css"], "前端"),
    # 客户端相关（优先于"开发"）
    (["客户端", "client", "ios", "android", "安卓", "移动端", "mobile", "app", "flutter", "rn", "react native", "swift", "kotlin", "objective-c", "oc"], "客户端"),
    # 运维相关
    (["运维", "ops", "devops", "sre", "dba", "运营维护", "系统管理", "infra", "infrastructure"], "运维"),
    # 产品相关
    (["产品", "product", "pm", "产品经理", "需求"], "产品"),
    # 项目经理相关
    (["项目经理", "项目", "pmo", "project manager", "scrum", "敏捷"], "项目经理"),
    # 开发（通用，优先级最低）
    (["开发", "dev", "developer", "程序员", "coder", "engineer", "工程师"], "开发"),
]


# ==================== 设计图JSON转HTML转换器 ====================

_UNITLESS_PROPERTIES = {'zIndex', 'fontWeight', 'opacity', 'flex', 'flexGrow', 'flexShrink', 'order'}

COMMON_CSS_FOR_DESIGN = """
body * {
  box-sizing: border-box;
  flex-shrink: 0;
}
body {
  font-family: PingFangSC-Regular, Roboto, Helvetica Neue, Helvetica, Tahoma,
    Arial, PingFang SC-Light, Microsoft YaHei;
}
input {
  background-color: transparent;
  border: 0;
}
button {
  margin: 0;
  padding: 0;
  border: 1px solid transparent;
  outline: none;
  background-color: transparent;
}
button:active {
  opacity: 0.6;
}
.flex-col {
  display: flex;
  flex-direction: column;
}
.flex-row {
  display: flex;
  flex-direction: row;
}
.justify-start {
  display: flex;
  justify-content: flex-start;
}
.justify-center {
  display: flex;
  justify-content: center;
}
.justify-end {
  display: flex;
  justify-content: flex-end;
}
.justify-evenly {
  display: flex;
  justify-content: space-evenly;
}
.justify-around {
  display: flex;
  justify-content: space-around;
}
.justify-between {
  display: flex;
  justify-content: space-between;
}
.align-start {
  display: flex;
  align-items: flex-start;
}
.align-center {
  display: flex;
  align-items: center;
}
.align-end {
  display: flex;
  align-items: flex-end;
}
"""


def _camel_to_kebab(s: str) -> str:
    """驼峰命名转换为CSS短横线命名"""
    return re.sub(r'([A-Z])', lambda m: f'-{m.group(1).lower()}', s)


def _format_css_value(key: str, value) -> str:
    """格式化CSS值，自动添加px单位"""
    if value is None:
        return ''
    if isinstance(value, (int, float)):
        if value == 0:
            return '0'
        return str(value) if key in _UNITLESS_PROPERTIES else f'{value}px'
    if isinstance(value, str):
        # 处理rgba格式
        if 'rgba(' in value:
            def replace_rgba(match):
                r, g, b, a = match.groups()
                alpha = float(a) if '.' in a else int(a)
                return f'rgba({r}, {g}, {b}, {alpha})'
            return re.sub(r'rgba\(([\d.]+),\s*([\d.]+),\s*([\d.]+),\s*([\d.]+)\)', replace_rgba, value)
        # 检查字符串形式的数字（fontSize可能是"14"或"14px"）
        if re.match(r'^\d+$', value) and key not in _UNITLESS_PROPERTIES:
            return '0' if value == '0' else f'{value}px'
    return str(value)


def _merge_padding(styles: dict) -> None:
    """合并padding四边属性"""
    pt = styles.get('paddingTop')
    pr = styles.get('paddingRight')
    pb = styles.get('paddingBottom')
    pl = styles.get('paddingLeft')
    
    if pt is not None and pr is not None and pb is not None and pl is not None:
        pt_val = pt or 0
        pr_val = pr or 0
        pb_val = pb or 0
        pl_val = pl or 0
        
        if pt_val == pb_val and pl_val == pr_val:
            if pt_val == pl_val:
                styles['padding'] = f'{pt_val}px'
            else:
                styles['padding'] = f'{pt_val}px {pr_val}px'
        else:
            styles['padding'] = f'{pt_val}px {pr_val}px {pb_val}px {pl_val}px'
        
        for k in ['paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft']:
            styles.pop(k, None)


def _merge_margin(styles: dict) -> None:
    """合并margin四边属性"""
    mt = styles.get('marginTop')
    mr = styles.get('marginRight')
    mb = styles.get('marginBottom')
    ml = styles.get('marginLeft')
    
    if mt is not None or mr is not None or mb is not None or ml is not None:
        mt_val = mt or 0
        mr_val = mr or 0
        mb_val = mb or 0
        ml_val = ml or 0
        
        if mt_val == 0 and mr_val == 0 and mb_val == 0 and ml_val == 0:
            pass  # 全是0，不输出
        elif mt_val == mb_val and ml_val == mr_val:
            if mt_val == ml_val:
                styles['margin'] = f'{mt_val}px'
            else:
                styles['margin'] = f'{mt_val}px {mr_val}px'
        else:
            styles['margin'] = f'{mt_val}px {mr_val}px {mb_val}px {ml_val}px'
        
        for k in ['marginTop', 'marginRight', 'marginBottom', 'marginLeft']:
            styles.pop(k, None)


def _should_use_flex(node: dict) -> bool:
    """判断节点是否使用flex布局"""
    if not node:
        return False
    node_style = node.get('style', {})
    node_props = node.get('props', {})
    node_props_style = node_props.get('style', {})
    style = {**node_style, **node_props_style}
    return style.get('display') == 'flex' or style.get('flexDirection') is not None


def _get_flex_classes(node: dict) -> list:
    """获取flex相关的CSS类名列表"""
    classes = []
    if not _should_use_flex(node):
        return classes
    
    node_style = node.get('style', {})
    node_props = node.get('props', {})
    node_props_style = node_props.get('style', {})
    style = {**node_style, **node_props_style}
    class_name = node_props.get('className', '')
    
    # Flex方向
    flex_direction = style.get('flexDirection')
    if flex_direction == 'column' or 'flex-col' in class_name:
        classes.append('flex-col')
    elif flex_direction == 'row' or 'flex-row' in class_name:
        classes.append('flex-row')
    
    # 主轴对齐
    justify = node.get('alignJustify', {}).get('justifyContent') or style.get('justifyContent')
    if justify == 'space-between':
        classes.append('justify-between')
    elif justify == 'center':
        classes.append('justify-center')
    elif justify == 'flex-end':
        classes.append('justify-end')
    elif justify == 'flex-start':
        classes.append('justify-start')
    elif justify == 'space-around':
        classes.append('justify-around')
    elif justify == 'space-evenly':
        classes.append('justify-evenly')
    
    # 交叉轴对齐
    align = node.get('alignJustify', {}).get('alignItems') or style.get('alignItems')
    if align == 'flex-start':
        classes.append('align-start')
    elif align == 'center':
        classes.append('align-center')
    elif align == 'flex-end':
        classes.append('align-end')
    
    return classes


def _clean_styles(node: dict, flex_classes: list) -> dict:
    """清理样式，移除被flex类覆盖的标准值"""
    node_props = node.get('props', {})
    props_style = node_props.get('style', {})
    styles = {}
    
    # 定义被flex类完全覆盖的标准值
    standard_justify = {'flex-start', 'center', 'flex-end', 'space-between', 'space-around', 'space-evenly'}
    standard_align = {'flex-start', 'center', 'flex-end'}
    
    for key, value in props_style.items():
        # 跳过display和flexDirection（由flex-col/flex-row类完全覆盖）
        if key in ('display', 'flexDirection'):
            if flex_classes:
                continue
        
        # justifyContent: 只跳过标准值
        if key == 'justifyContent' and flex_classes:
            if value in standard_justify:
                continue
        
        # alignItems: 只跳过标准值
        if key == 'alignItems' and flex_classes:
            if value in standard_align:
                continue
        
        # 跳过static定位
        if key == 'position' and value == 'static':
            continue
        
        # 跳过visible溢出
        if key == 'overflow' and value == 'visible':
            continue
        
        styles[key] = value
    
    # 合并padding和margin
    if any(k in styles for k in ['paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft']):
        _merge_padding(styles)
    if any(k in styles for k in ['marginTop', 'marginRight', 'marginBottom', 'marginLeft']):
        _merge_margin(styles)
    
    return styles


def _get_loop_arr(node: dict) -> list:
    """取节点的 loop 数据：优先 loop，其次 loopData。"""
    if not node:
        return []
    arr = node.get('loop') or node.get('loopData')
    return arr if isinstance(arr, list) else []


def _generate_css(node: dict, css_rules: dict, loop_suffixes: list | None = None) -> None:
    """递归生成CSS规则。loop_suffixes 非空时，当前子树为循环模板，类名按 -0/-1/... 展开。"""
    if not node:
        return

    loop_arr = _get_loop_arr(node) if node.get('loopType') else []
    if loop_arr and not loop_suffixes:
        loop_suffixes = [str(i) for i in range(len(loop_arr))]

    node_props = node.get('props', {})
    class_name = node_props.get('className')
    if class_name:
        flex_classes = _get_flex_classes(node)
        styles = _clean_styles(node, flex_classes)
        style_entries = list(styles.items())
        if style_entries or node.get('type') == 'lanhutext':
            css_props = []
            for key, value in style_entries:
                css_key = _camel_to_kebab(key)
                css_value = _format_css_value(key, value)
                if css_value:
                    css_props.append(f'  {css_key}: {css_value};')
            content = '\n'.join(css_props) if css_props else ''
        else:
            content = ''
        if loop_suffixes:
            for suf in loop_suffixes:
                css_rules[f'{class_name}-{suf}'] = content
        else:
            css_rules[class_name] = content

    children = node.get('children', [])
    for child in children:
        _generate_css(child, css_rules, loop_suffixes)


def _resolve_loop_placeholder(value: str, loop_item: dict) -> str:
    """this.item.xxx -> loop_item.get('xxx', '')"""
    if not value or not isinstance(loop_item, dict):
        return value or ''
    s = str(value).strip()
    m = re.match(r'^this\.item\.(\w+)$', s)
    return loop_item.get(m.group(1), '') if m else value


def _generate_html(
    node: dict,
    indent: int = 2,
    loop_context: tuple[list, int] | None = None,
) -> str:
    """递归生成HTML结构。loop_context=(loop_list, index) 时当前为循环项，类名加 -index，占位符用 loop 数据替换。"""
    if not node:
        return ''

    loop_item = loop_context[0][loop_context[1]] if loop_context else None
    loop_index = loop_context[1] if loop_context else None

    spaces = ' ' * indent
    flex_classes = _get_flex_classes(node)
    node_props = node.get('props', {})
    class_name = node_props.get('className', '')
    if loop_index is not None and class_name:
        class_name = f'{class_name}-{loop_index}'
    all_classes = ' '.join([c for c in [class_name] + flex_classes if c])

    node_type = node.get('type')

    if node_type == 'lanhutext':
        text = node.get('data', {}).get('value') or node_props.get('text') or ''
        if loop_item is not None and text and re.match(r'^this\.item\.\w+$', str(text).strip()):
            text = _resolve_loop_placeholder(text, loop_item)
        elif text and re.match(r'^this\.item\.\w+$', str(text).strip()):
            text = ''
        return f'{spaces}<span class="{all_classes}">{text}</span>'

    if node_type == 'lanhuimage':
        src = node.get('data', {}).get('value') or node_props.get('src') or ''
        if loop_item is not None and src and re.match(r'^this\.item\.\w+$', str(src).strip()):
            src = _resolve_loop_placeholder(src, loop_item)
        elif src and re.match(r'^this\.item\.\w+$', str(src).strip()):
            src = ''
        return f'{spaces}<img\n{spaces}  class="{all_classes}"\n{spaces}  referrerpolicy="no-referrer"\n{spaces}  src="{src}"\n{spaces}/>'

    if node_type == 'lanhubutton':
        children = node.get('children', [])
        children_html = '\n'.join([
            _generate_html(c, indent + 2, loop_context) for c in children
        ])
        return f'{spaces}<button class="{all_classes}">\n{children_html}\n{spaces}</button>'

    tag = 'div'
    children = node.get('children', [])
    loop_arr = _get_loop_arr(node) if node.get('loopType') else []

    if loop_arr and loop_context is None:
        parts = []
        for i in range(len(loop_arr)):
            ctx = (loop_arr, i)
            for child in children:
                parts.append(_generate_html(child, indent + 2, ctx))
        children_html = '\n'.join(parts)
        return f'{spaces}<{tag} class="{all_classes}">\n{children_html}\n{spaces}</{tag}>'

    if children:
        children_html = '\n'.join([
            _generate_html(c, indent + 2, loop_context) for c in children
        ])
        return f'{spaces}<{tag} class="{all_classes}">\n{children_html}\n{spaces}</{tag}>'
    return f'{spaces}<{tag} class="{all_classes}"></{tag}>'


def convert_lanhu_to_html(json_data: dict) -> str:
    """
    将蓝湖设计图JSON转换为HTML+CSS
    
    Args:
        json_data: 蓝湖设计图Schema JSON
        
    Returns:
        完整的HTML字符串（含嵌入式CSS）
    """
    css_rules = {}
    
    # 生成CSS
    _generate_css(json_data, css_rules)
    
    # 组装CSS字符串
    css_parts = []
    for class_name, props in css_rules.items():
        if props:
            css_parts.append(f'.{class_name} {{\n{props}\n}}')
        else:
            css_parts.append(f'.{class_name} {{\n}}')
    
    css_string = '\n\n'.join(css_parts)
    css_string += COMMON_CSS_FOR_DESIGN
    
    # 生成HTML
    body_html = _generate_html(json_data, 4)
    
    html = f'''<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Document</title>
    <style>
{css_string}
    </style>
  </head>
  <body>
{body_html}
  </body>
</html>'''
    
    return html


def _extract_design_tokens(sketch_data: dict) -> str:
    """
    从 Sketch JSON 中提取高风险元素的设计参数，输出紧凑文本供 AI 校验。
    只提取含渐变、非均匀圆角、边框、阴影的**真实可见**元素，过滤掉 Sketch 内部节点。
    """
    import math

    NOISE_TYPES = {'color', 'gradient', 'colorStop', 'colorControl'}

    def _get_dimensions(obj: dict) -> tuple:
        """获取元素实际尺寸，优先从 frame 字段读取"""
        frame = obj.get('ddsOriginFrame') or obj.get('layerOriginFrame') or {}
        x = frame.get('x', obj.get('left', 0)) or 0
        y = frame.get('y', obj.get('top', 0)) or 0
        w = frame.get('width', obj.get('width', 0)) or 0
        h = frame.get('height', obj.get('height', 0)) or 0
        return x, y, w, h

    def _simplify_fill(fill: dict) -> str | None:
        if not fill.get('isEnabled', True):
            return None
        fill_type = fill.get('fillType', 0)
        if fill_type == 0:
            color = fill.get('color', {})
            return f"solid({color.get('value', 'unknown')})"
        if fill_type == 1:
            gradient = fill.get('gradient', {})
            stops = gradient.get('colorStops', [])
            from_pt = gradient.get('from', {})
            to_pt = gradient.get('to', {})
            dx = to_pt.get('x', 0.5) - from_pt.get('x', 0.5)
            dy = to_pt.get('y', 0) - from_pt.get('y', 0)
            angle = round(math.degrees(math.atan2(dx, dy))) % 360
            parts = []
            for s in stops:
                c = s.get('color', {}).get('value', 'unknown')
                p = s.get('position', 0)
                parts.append(f"{c} {round(p * 100)}%")
            return f"linear-gradient({angle}deg, {', '.join(parts)})"
        return None

    def _simplify_border(border: dict) -> str | None:
        if not border.get('isEnabled', True):
            return None
        color = border.get('color', {}).get('value', 'unknown')
        thickness = border.get('thickness', 1)
        pos_map = {'内边框': 'inside', '外边框': 'outside', '中心边框': 'center'}
        pos = pos_map.get(border.get('position', ''), border.get('position', 'center'))
        return f"{thickness}px {pos} {color}"

    def _simplify_shadow(shadow: dict) -> str | None:
        if not shadow.get('isEnabled', True):
            return None
        color = shadow.get('color', {}).get('value', 'unknown')
        x = shadow.get('offsetX', 0)
        y = shadow.get('offsetY', 0)
        blur = shadow.get('blurRadius', 0)
        spread = shadow.get('spread', 0)
        return f"{color} {x}px {y}px {blur}px {spread}px"

    def _has_only_transparent_solid(fills: list) -> bool:
        """判断 fills 是否只有透明纯色填充（无视觉意义）"""
        for f in fills:
            if not f.get('isEnabled', True):
                continue
            if f.get('fillType', 0) == 0:
                color = f.get('color', {})
                val = color.get('value', '')
                if 'rgba' in val and ',0)' in val.replace(' ', ''):
                    continue
                alpha = color.get('alpha', color.get('a', 1))
                if alpha == 0:
                    continue
            return False
        return True

    def _is_high_risk(obj: dict) -> bool:
        obj_type = (obj.get('type') or obj.get('ddsType') or '').lower()
        if obj_type in NOISE_TYPES:
            return False

        _, _, w, h = _get_dimensions(obj)
        if w < 2 and h < 2:
            return False

        has_gradient_fill = False
        fills = obj.get('fills', [])
        for f in fills:
            if f.get('isEnabled', True) and f.get('fillType') == 1:
                has_gradient_fill = True
                break
        if has_gradient_fill:
            return True

        if obj.get('borders'):
            for b in obj['borders']:
                if b.get('isEnabled', True):
                    return True

        radius = obj.get('radius')
        if isinstance(radius, list) and len(set(radius)) > 1:
            return True

        opacity = obj.get('opacity')
        if opacity is not None and opacity < 100:
            if _has_only_transparent_solid(fills) and not obj.get('borders') and not obj.get('shadows'):
                return False
            return True

        if obj.get('shadows'):
            for s in obj['shadows']:
                if s.get('isEnabled', True):
                    return True

        return False

    tokens = []

    def _build_path(parent_path: str, name: str) -> str:
        return f"{parent_path}/{name}" if parent_path else name

    def _walk(obj: dict, parent_path: str = ""):
        if not obj or not isinstance(obj, dict):
            return
        if not obj.get('isVisible', True):
            return

        name = obj.get('name', '')
        current_path = _build_path(parent_path, name)

        if _is_high_risk(obj):
            obj_type = obj.get('type') or obj.get('ddsType') or 'unknown'
            x, y, w, h = _get_dimensions(obj)

            lines = [f'[{obj_type}] "{name}" @({int(x)},{int(y)}) {int(w)}x{int(h)}']
            if parent_path:
                lines[0] += f'  path: {current_path}'

            radius = obj.get('radius')
            if radius:
                if isinstance(radius, list):
                    if len(set(radius)) == 1:
                        lines.append(f'  radius: {radius[0]}')
                    else:
                        lines.append(f'  radius: {radius}')
                else:
                    lines.append(f'  radius: {radius}')

            for f in obj.get('fills', []):
                s = _simplify_fill(f)
                if s:
                    lines.append(f'  fill: {s}')

            for b in obj.get('borders', []):
                s = _simplify_border(b)
                if s:
                    lines.append(f'  border: {s}')

            opacity = obj.get('opacity')
            if opacity is not None and opacity < 100:
                lines.append(f'  opacity: {opacity}%')

            for sh in obj.get('shadows', []):
                s = _simplify_shadow(sh)
                if s:
                    lines.append(f'  shadow: {s}')

            tokens.append('\n'.join(lines))

        for child in obj.get('layers', []):
            _walk(child, current_path)

    if sketch_data.get('artboard') and sketch_data['artboard'].get('layers'):
        for layer in sketch_data['artboard']['layers']:
            _walk(layer)
    elif sketch_data.get('info'):
        for item in sketch_data['info']:
            _walk(item)
            for value in item.values():
                if isinstance(value, dict):
                    _walk(value)
                elif isinstance(value, list):
                    for v in value:
                        if isinstance(v, dict):
                            _walk(v)

    if not tokens:
        return ""
    return '\n\n'.join(tokens)


def _oc_to_css(oc_code: str) -> str:
    """将蓝湖标注面板的 Objective-C 代码转换为 CSS 属性。"""
    import re
    css = []
    m = re.search(r'CGRectMake\(([\d.]+),([\d.]+),([\d.]+),([\d.]+)\)', oc_code)
    if m:
        css.append(f"left:{m.group(1)}px;top:{m.group(2)}px;width:{m.group(3)}px;height:{m.group(4)}px")

    for pat in re.finditer(r'backgroundColor = \[UIColor colorWithRed:([\d]+)/255\.0 green:([\d]+)/255\.0 blue:([\d]+)/255\.0 alpha:([\d.]+)\]', oc_code):
        r, g, b, a = pat.group(1), pat.group(2), pat.group(3), pat.group(4)
        css.append(f"background-color:rgba({r},{g},{b},{a})")

    m = re.search(r'cornerRadius = ([\d.]+)', oc_code)
    if m:
        css.append(f"border-radius:{m.group(1)}px")

    shadow_color = re.search(r'shadowColor = \[UIColor colorWithRed:([\d]+)/255\.0 green:([\d]+)/255\.0 blue:([\d]+)/255\.0 alpha:([\d.]+)\]', oc_code)
    shadow_offset = re.search(r'shadowOffset = CGSizeMake\(([\d.-]+),([\d.-]+)\)', oc_code)
    shadow_radius = re.search(r'shadowRadius = ([\d.]+)', oc_code)
    if shadow_color and shadow_offset:
        sr, sg, sb, sa = shadow_color.group(1), shadow_color.group(2), shadow_color.group(3), shadow_color.group(4)
        sx, sy = shadow_offset.group(1), shadow_offset.group(2)
        blur = shadow_radius.group(1) if shadow_radius else '0'
        css.append(f"box-shadow:{sx}px {sy}px {blur}px rgba({sr},{sg},{sb},{sa})")

    border_w = re.search(r'borderWidth = ([\d.]+)', oc_code)
    border_c = re.search(r'borderColor = \[UIColor colorWithRed:([\d]+)/255\.0 green:([\d]+)/255\.0 blue:([\d]+)/255\.0 alpha:([\d.]+)\]', oc_code)
    if border_w and border_c:
        bw = border_w.group(1)
        br, bg, bb, ba = border_c.group(1), border_c.group(2), border_c.group(3), border_c.group(4)
        css.append(f"border:{bw}px solid rgba({br},{bg},{bb},{ba})")

    if 'fontWithName:@"' in oc_code:
        fm = re.search(r'fontWithName:@"([^"]+)" size: ([\d.]+)', oc_code)
        if fm:
            css.append(f"font-family:\"{fm.group(1)}\",sans-serif;font-size:{fm.group(2)}px")

    fc = re.search(r'ForegroundColorAttributeName: \[UIColor colorWithRed:([\d]+)/255\.0 green:([\d]+)/255\.0 blue:([\d]+)/255\.0 alpha:([\d.]+)\]', oc_code)
    if fc:
        css.append(f"color:rgba({fc.group(1)},{fc.group(2)},{fc.group(3)},{fc.group(4)})")

    return ';'.join(css)


def convert_sketch_to_html(sketch_data: dict, design_scale: float = 2.0,
                           design_img_url: str = "") -> str:
    """
    将 Sketch/PSD JSON 转换为 HTML+CSS。
    策略：设计原图 background-image 裁剪 + 文字/切图叠加 + data-css 标注。
    """
    import math, re
    scale = design_scale or 2.0

    def px(v):
        if v is None:
            return 0
        return round(float(v) / scale * 10) / 10

    def color_css(c, opacity=100):
        if not c or not isinstance(c, dict):
            return None
        if 'value' in c:
            return c['value']
        r = round(c.get('red', c.get('r', 0)))
        g = round(c.get('green', c.get('g', 0)))
        b = round(c.get('blue', c.get('b', 0)))
        a = round(opacity / 100, 2) if opacity < 100 else 1
        return f"rgba({r},{g},{b},{a})" if a < 1 else f"rgb({r},{g},{b})"

    def get_opacity(layer):
        bo = layer.get('blendOptions') or {}
        if 'opacity' in bo:
            op = bo['opacity']
            return op.get('value', 100) if isinstance(op, dict) else op
        return 100

    def extract_border_radius(layer):
        path = layer.get('path') or {}
        comps = path.get('pathComponents') or []
        if not comps:
            return None
        origin = comps[0].get('origin') or {}
        radii = origin.get('radii')
        if not radii:
            return None
        r = [px(v) for v in radii]
        if len(set(r)) == 1 and r[0] > 0:
            return f"{r[0]}px"
        if any(v > 0 for v in r):
            return f"{r[0]}px {r[1]}px {r[2]}px {r[3]}px"
        return None

    def extract_shadow(effects):
        shadows = []
        for key in ('dropShadow', 'innerShadow'):
            fx = effects.get(key)
            if not fx or not fx.get('enabled'):
                continue
            c = fx.get('color') or {}
            color = color_css(c)
            if not color:
                continue
            op_obj = fx.get('opacity') or {}
            op_val = op_obj.get('value', 100) if isinstance(op_obj, dict) else 100
            if op_val < 100:
                r = round(c.get('red', c.get('r', 0)))
                g = round(c.get('green', c.get('g', 0)))
                b = round(c.get('blue', c.get('b', 0)))
                color = f"rgba({r},{g},{b},{round(op_val/100, 2)})"

            angle_obj = fx.get('localLightingAngle') or {}
            angle_deg = angle_obj.get('value', 90) if isinstance(angle_obj, dict) else 90
            angle_rad = math.radians(angle_deg)
            dist = px(fx.get('distance', 0))
            blur = px(fx.get('blur', 0))
            spread = px(fx.get('chokeMatte', 0))
            ox = round(-dist * math.cos(angle_rad) * 10) / 10
            oy = round(dist * math.sin(angle_rad) * 10) / 10

            inset = "inset " if key == 'innerShadow' else ""
            spread_str = f" {spread}px" if spread else ""
            shadows.append(f"{inset}{ox}px {oy}px {blur}px{spread_str} {color}")
        return ','.join(shadows) if shadows else None

    def extract_border(effects):
        stroke = effects.get('frameFX') or effects.get('solidFill')
        if not stroke or not stroke.get('enabled'):
            return None
        size = px(stroke.get('size', 1))
        c = stroke.get('color') or {}
        color = color_css(c)
        if color:
            return f"{size}px solid {color}"
        return None

    def parse_font_weight(style_name):
        if not style_name:
            return None
        m = re.search(r'(\d+)', style_name)
        return int(m.group(1)) if m else None

    layers = []
    board_w = 375
    board_h = 667

    if 'board' in sketch_data:
        board = sketch_data['board']
        board_w = px(board.get('width', 750))
        board_h = px(board.get('height', 1334))
        raw_layers = board.get('layers', [])

        def _flatten(layer):
            if not layer or not isinstance(layer, dict):
                return
            if layer.get('visible') is False:
                return
            w = layer.get('width', 0) or 0
            h = layer.get('height', 0) or 0
            if w == 0 and h == 0:
                for child in reversed(layer.get('layers', [])):
                    _flatten(child)
                return
            ltype = layer.get('type', '')
            if ltype == 'layerSection':
                images = layer.get('images') or {}
                if images.get('png_xxxhd') or images.get('svg'):
                    layers.append(layer)
                else:
                    for child in reversed(layer.get('layers', [])):
                        _flatten(child)
                return
            layers.append(layer)

        for l in reversed(raw_layers):
            _flatten(l)

    css_rules = []
    html_parts = []
    image_url_mapping = {}
    layer_annotations = []

    for idx, L in enumerate(layers):
        cls = f"el{idx + 1}"
        ltype = L.get('type', '')
        name = L.get('name', '')
        left = px(L.get('left', 0))
        top = px(L.get('top', 0))
        w = px(L.get('width', 0))
        h = px(L.get('height', 0))

        opacity = get_opacity(L)
        effects = L.get('layerEffects') or {}

        annot = {
            'name': name,
            'type': ltype,
            'css': {
                'position': 'absolute',
                'left': f'{left}px', 'top': f'{top}px',
                'width': f'{w}px', 'height': f'{h}px',
            }
        }

        props = [
            "position:absolute",
            f"left:{left}px", f"top:{top}px",
            f"width:{w}px", f"height:{h}px",
        ]

        if opacity < 100:
            op_css = round(opacity / 100, 2)
            props.append(f"opacity:{op_css}")
            annot['css']['opacity'] = str(op_css)

        br = extract_border_radius(L)
        if br:
            props.append(f"border-radius:{br}")
            props.append("overflow:hidden")
            annot['css']['border-radius'] = br

        shadow = extract_shadow(effects)
        if shadow:
            annot['css']['box-shadow'] = shadow

        border = extract_border(effects)
        if border:
            annot['css']['border'] = border

        text_content = ""
        is_slice = False
        slice_url = ""

        images = L.get('images') or {}
        if images.get('png_xxxhd') or images.get('svg'):
            is_slice = True
            slice_url = images.get('png_xxxhd') or images.get('svg')
            local_name = f"{name.replace('/', '_').replace(' ', '_')}.png"
            local_path = f"./assets/slices/{local_name}"
            image_url_mapping[local_path] = slice_url
            annot['slice_url'] = slice_url

        if ltype == 'textLayer' and L.get('textInfo'):
            ti = L['textInfo']
            text_content = ti.get('text', '')
            annot['text'] = text_content
            props.append('z-index:10')
            text_color = color_css(ti.get('color'), opacity)
            if text_color:
                props.append(f"color:{text_color}")
                annot['css']['color'] = text_color
            font_size = px(ti.get('size', 0))
            if font_size:
                props.append(f"font-size:{font_size}px")
                annot['css']['font-size'] = f'{font_size}px'
            font_name = ti.get('fontPostScriptName') or ti.get('fontName', '')
            if font_name:
                props.append(
                    f'font-family:"{font_name}","PingFang SC",'
                    f'"Microsoft YaHei","Hiragino Sans GB",sans-serif'
                )
                annot['css']['font-family'] = font_name
            font_style_name = ti.get('fontStyleName', '')
            fw = parse_font_weight(font_style_name)
            if fw:
                props.append(f"font-weight:{fw}")
                annot['css']['font-weight'] = str(fw)
            elif font_style_name:
                annot['css']['font-weight'] = font_style_name
            if ti.get('bold') and not fw:
                props.append("font-weight:bold")
            if ti.get('italic'):
                props.append("font-style:italic")
            just = ti.get('justification', 'left')
            if just != 'left':
                props.append(f"text-align:{just}")
                annot['css']['text-align'] = just
            lines = [ln for ln in text_content.split('\r') if ln]
            line_count = max(len(lines), 1)
            if line_count > 1 and h > 0 and font_size > 0:
                lh = round(h / line_count * 10) / 10
                props.append(f"line-height:{lh}px")
            else:
                props.append("line-height:1")
            props.append("white-space:pre-wrap")
            props.append("overflow:hidden")
            props.append("word-break:break-all")
        elif is_slice:
            props.append('z-index:5')
        else:
            fill = (L.get('fill') or {})
            fill_color = color_css(fill.get('color'), opacity)
            if fill_color:
                annot['css']['background-color'] = fill_color

        css_rules.append(f".{cls}{{{';'.join(props)}}}")

        safe_name = (name or "").replace('"', '&quot;')
        css_data = '; '.join(f'{k}: {v}' for k, v in annot['css'].items())
        safe_css = css_data.replace('"', '&quot;')
        if text_content:
            safe_text = text_content.replace('<', '&lt;').replace('>', '&gt;').replace('\r', '\n')
            html_parts.append(
                f'<div class="{cls}" title="{safe_name}" data-css="{safe_css}">'
                f'{safe_text}</div>'
            )
        elif is_slice:
            html_parts.append(
                f'<img class="{cls}" title="{safe_name}" data-css="{safe_css}" '
                f'src="{slice_url}" referrerpolicy="no-referrer" />'
            )
        else:
            html_parts.append(
                f'<div class="{cls}" title="{safe_name}" data-css="{safe_css}"></div>'
            )

        layer_annotations.append(annot)

    html = (
        f'<!DOCTYPE html><html><head><meta charset="UTF-8">'
        f'<meta name="referrer" content="no-referrer">'
        f'<meta name="viewport" content="width=device-width,initial-scale=1.0">'
        f'<title>Design</title><style>'
        f'*{{margin:0;padding:0;box-sizing:border-box}}img{{display:block}}'
        f'.design{{position:relative;width:{board_w}px;height:{board_h}px;'
        f'overflow:hidden;margin:0 auto'
        + (f';background:url({design_img_url}) no-repeat;'
           f'background-size:{board_w}px {board_h}px'
           if design_img_url else '')
        + '}}\n'
        + '\n'.join(css_rules)
        + '</style></head><body><div class="design">\n'
        + '\n'.join(html_parts)
        + '\n</div></body></html>'
    )

    return html, image_url_mapping, layer_annotations


# JS 脚本：注入蓝湖页面，遍历所有图层，点击提取标注面板数据
LANHU_EXTRACT_JS = r'''
(async () => {
  const el = document.querySelector('.layer_interactive');
  let vm = null; let node = el;
  while (node) { if (node.__vue__) { vm = node.__vue__; break; } node = node.parentElement; }
  const layers = vm.g_detail?.layers;
  const items = document.querySelectorAll('.layers_item');
  const imgEl = document.querySelector('.big-img');
  const designImgUrl = imgEl?.src || '';
  const dw = (layers[0]?.width || 750) / 2;
  const dh = (layers[0]?.height || 1334) / 2;
  const px = v => Math.round(v / 2 * 10) / 10;

  const results = [];
  for (let i = 1; i < layers.length && i < items.length; i++) {
    const L = layers[i];
    if (!L.visible || (!L.width && !L.height)) continue;
    items[i].dispatchEvent(new MouseEvent('mousedown', {bubbles:true, clientX:100, clientY:100}));
    items[i].dispatchEvent(new MouseEvent('mouseup', {bubbles:true}));
    items[i].dispatchEvent(new MouseEvent('click', {bubbles:true}));
    await new Promise(r => setTimeout(r, 50));
    results.push({
      name: L.name, type: L.type,
      left: px(L.left), top: px(L.top), width: px(L.width), height: px(L.height),
      images: L.images || {},
      textInfo: L.textInfo || null,
      code: document.querySelector('.code_box')?.textContent?.substring(0, 1000) || ''
    });
  }
  return JSON.stringify({ designImgUrl, canvasW: dw, canvasH: dh, layers: results });
})()
'''


def _extract_full_annotations_from_sketch(sketch_data: dict, design_scale: float = 2.0) -> str:
    """
    当 store_schema_revise 失败时，从原始 Sketch JSON 中提取完整的标注信息，
    包括画布信息、图层层级结构（文本/形状/图片）、颜色/字体/尺寸/位置/特效等，
    生成结构化文本供 AI 还原设计。

    design_scale: 设计稿缩放比（如 iOS @2x 则为 2.0），用于将 px 转换为逻辑点。
    """
    import math

    scale = design_scale or 2.0

    def _rgb_str(color: dict) -> str:
        r = round(color.get('red', color.get('r', 0)))
        g = round(color.get('green', color.get('g', 0)))
        b = round(color.get('blue', color.get('b', 0)))
        return f"rgb({r},{g},{b})"

    def _rgba_str(color: dict, opacity_val: float = 100) -> str:
        r = round(color.get('red', color.get('r', 0)))
        g = round(color.get('green', color.get('g', 0)))
        b = round(color.get('blue', color.get('b', 0)))
        a = round(opacity_val / 100, 2) if opacity_val < 100 else 1
        if a < 1:
            return f"rgba({r},{g},{b},{a})"
        return f"rgb({r},{g},{b})"

    def _px(val) -> str:
        """将设计稿 px 转换为逻辑像素字符串"""
        if val is None:
            return "0"
        return str(round(float(val) / scale, 1))

    def _extract_opacity(layer: dict) -> float:
        bo = layer.get('blendOptions', {})
        if 'opacity' in bo:
            op = bo['opacity']
            if isinstance(op, dict):
                return op.get('value', 100)
            return op
        return 100

    def _extract_fill_color(layer: dict):
        fill = layer.get('fill', {})
        if not fill:
            return None
        color = fill.get('color')
        if not color:
            return None
        opacity = _extract_opacity(layer)
        return _rgba_str(color, opacity)

    def _extract_shadow_str(shadow_data: dict):
        if not shadow_data.get('enabled', True):
            return None
        color = shadow_data.get('color', {})
        opacity = shadow_data.get('opacity', {})
        op_val = opacity.get('value', 100) if isinstance(opacity, dict) else opacity
        dx = shadow_data.get('localLightingAngle', {})
        distance = shadow_data.get('distance', 0)
        blur = shadow_data.get('blur', 0)
        spread = shadow_data.get('chokeMatte', 0)
        angle_raw = shadow_data.get('localLightingAngle', {})
        angle = angle_raw.get('value', 120) if isinstance(angle_raw, dict) else (angle_raw or 120)
        rad = math.radians(angle)
        x_off = round(distance * math.cos(rad), 1)
        y_off = round(distance * math.sin(rad), 1)
        color_str = _rgba_str(color, op_val)
        return f"{color_str} {_px(x_off)}px {_px(y_off)}px {_px(blur)}px {_px(spread)}px"

    def _extract_stroke_str(frame_fx: dict):
        if not frame_fx.get('enabled', True):
            return None
        size = frame_fx.get('size', 0)
        color = frame_fx.get('color', {})
        opacity = frame_fx.get('opacity', {})
        op_val = opacity.get('value', 100) if isinstance(opacity, dict) else opacity
        style = frame_fx.get('style', 'outsetFrame')
        pos_map = {'outsetFrame': 'outside', 'insetFrame': 'inside', 'centeredFrame': 'center'}
        pos = pos_map.get(style, 'outside')
        color_str = _rgba_str(color, op_val)
        return f"{_px(size)}px {pos} {color_str}"

    lines = []
    board = sketch_data.get('board', {})
    device = sketch_data.get('device', '')
    psd_name = sketch_data.get('psdName', '')
    board_w = board.get('width', 0)
    board_h = board.get('height', 0)
    board_fill = board.get('fill', {})
    board_color = _rgb_str(board_fill.get('color', {})) if board_fill.get('color') else '#FFFFFF'

    lines.append("=" * 60)
    lines.append("设计标注信息（从原始 Sketch/PSD 数据提取）")
    lines.append("=" * 60)
    lines.append(f"设计稿名称: {psd_name}")
    lines.append(f"设备: {device}  |  缩放: @{int(scale)}x")
    lines.append(f"画布尺寸: {_px(board_w)}x{_px(board_h)} (逻辑像素)")
    lines.append(f"画布背景色: {board_color}")
    lines.append("")
    lines.append("以下所有尺寸/坐标均为逻辑像素（已除以 @{0}x）".format(int(scale)))
    lines.append("-" * 60)

    text_layers = []
    shape_layers = []
    image_layers = []
    group_structure = []

    def _walk_layer(layer: dict, depth: int = 0, parent_path: str = ""):
        if not layer or not isinstance(layer, dict):
            return
        vis = layer.get('visible', True)
        if vis is False:
            return

        name = layer.get('name', '?')
        ltype = layer.get('type', '?')
        w = layer.get('width', 0) or 0
        h = layer.get('height', 0) or 0
        left = layer.get('left', 0) or 0
        top = layer.get('top', 0) or 0
        current_path = f"{parent_path}/{name}" if parent_path else name

        if w == 0 and h == 0:
            for child in layer.get('layers', []):
                _walk_layer(child, depth, current_path)
            return

        opacity = _extract_opacity(layer)

        if ltype == 'textLayer':
            ti = layer.get('textInfo', {})
            text = ti.get('text', '')
            color = ti.get('color', {})
            size = ti.get('size', 0)
            font = ti.get('fontPostScriptName', '')
            bold = ti.get('bold', False)
            italic = ti.get('italic', False)
            justify = ti.get('justification', 'left')
            leading = ti.get('leading')
            tracking = ti.get('tracking')
            le = layer.get('layerEffects', {})

            entry = {
                'name': name,
                'path': current_path,
                'text': text,
                'x': _px(left), 'y': _px(top), 'w': _px(w), 'h': _px(h),
                'color': _rgba_str(color, opacity) if color else None,
                'fontSize': _px(size) if size else None,
                'font': font,
                'bold': bold,
                'italic': italic,
                'justify': justify,
                'leading': _px(leading) if leading else None,
                'tracking': tracking,
                'stroke': None,
                'shadow': None,
            }
            if 'frameFX' in le:
                entry['stroke'] = _extract_stroke_str(le['frameFX'])
            if 'dropShadow' in le:
                entry['shadow'] = _extract_shadow_str(le['dropShadow'])
            text_layers.append(entry)

        elif ltype == 'shapeLayer':
            fill_color = _extract_fill_color(layer)
            le = layer.get('layerEffects', {})

            entry = {
                'name': name,
                'path': current_path,
                'x': _px(left), 'y': _px(top), 'w': _px(w), 'h': _px(h),
                'fill': fill_color,
                'opacity': opacity if opacity < 100 else None,
                'stroke': None,
                'shadows': [],
                'innerShadows': [],
                'effects': [],
            }

            if 'frameFX' in le:
                entry['stroke'] = _extract_stroke_str(le['frameFX'])

            for shadow_key in ['dropShadow', 'dropShadowMulti']:
                if shadow_key in le:
                    sd = le[shadow_key]
                    if isinstance(sd, list):
                        for s in sd:
                            ss = _extract_shadow_str(s)
                            if ss:
                                entry['shadows'].append(ss)
                    elif isinstance(sd, dict):
                        ss = _extract_shadow_str(sd)
                        if ss:
                            entry['shadows'].append(ss)

            for shadow_key in ['innerShadow', 'innerShadowMulti']:
                if shadow_key in le:
                    sd = le[shadow_key]
                    if isinstance(sd, list):
                        for s in sd:
                            ss = _extract_shadow_str(s)
                            if ss:
                                entry['innerShadows'].append(f"inset {ss}")
                    elif isinstance(sd, dict):
                        ss = _extract_shadow_str(sd)
                        if ss:
                            entry['innerShadows'].append(f"inset {ss}")

            for fx_name in ['bevelEmboss', 'outerGlow', 'innerGlow', 'patternFill']:
                if fx_name in le and le[fx_name].get('enabled', True):
                    entry['effects'].append(fx_name)

            shape_layers.append(entry)

        elif ltype == 'layer':
            if w > 10 and h > 10:
                image_layers.append({
                    'name': name,
                    'path': current_path,
                    'x': _px(left), 'y': _px(top), 'w': _px(w), 'h': _px(h),
                    'opacity': opacity if opacity < 100 else None,
                })

        elif ltype == 'layerSection':
            group_structure.append({
                'name': name,
                'depth': depth,
                'x': _px(left), 'y': _px(top), 'w': _px(w), 'h': _px(h),
            })

        for child in layer.get('layers', []):
            _walk_layer(child, depth + 1, current_path)

    board_layers = board.get('layers', [])
    for layer in board_layers:
        _walk_layer(layer)

    if group_structure:
        lines.append("")
        lines.append("📂 图层组结构 (布局参考):")
        for g in group_structure:
            indent = "  " * g['depth']
            lines.append(f"  {indent}[组] \"{g['name']}\" @({g['x']},{g['y']}) {g['w']}x{g['h']}")

    if text_layers:
        lines.append("")
        lines.append("📝 文本图层:")
        for t in text_layers:
            lines.append(f"  \"{t['text']}\"")
            lines.append(f"    位置: ({t['x']},{t['y']}) {t['w']}x{t['h']}")
            parts = []
            if t['fontSize']:
                parts.append(f"font-size: {t['fontSize']}px")
            if t['font']:
                parts.append(f"font-family: {t['font']}")
            if t['bold']:
                parts.append("font-weight: bold")
            if t['italic']:
                parts.append("font-style: italic")
            if t['color']:
                parts.append(f"color: {t['color']}")
            if t['justify'] and t['justify'] != 'left':
                parts.append(f"text-align: {t['justify']}")
            if t['leading']:
                parts.append(f"line-height: {t['leading']}px")
            if t['tracking']:
                parts.append(f"letter-spacing: {t['tracking']}")
            if parts:
                lines.append(f"    样式: {'; '.join(parts)}")
            if t['stroke']:
                lines.append(f"    描边: {t['stroke']}")
            if t['shadow']:
                lines.append(f"    阴影: {t['shadow']}")

    if shape_layers:
        lines.append("")
        lines.append("🔷 形状图层:")
        for s in shape_layers:
            lines.append(f"  \"{s['name']}\" ({s['path']})")
            lines.append(f"    位置: ({s['x']},{s['y']}) {s['w']}x{s['h']}")
            parts = []
            if s['fill']:
                parts.append(f"fill: {s['fill']}")
            if s['opacity'] is not None:
                parts.append(f"opacity: {s['opacity']}%")
            if s['stroke']:
                parts.append(f"border: {s['stroke']}")
            if parts:
                lines.append(f"    样式: {'; '.join(parts)}")
            all_shadows = s['shadows'] + s['innerShadows']
            if all_shadows:
                lines.append(f"    box-shadow: {', '.join(all_shadows)}")
            if s['effects']:
                lines.append(f"    特效: {', '.join(s['effects'])}")

    if image_layers:
        lines.append("")
        lines.append("🖼️ 图片/位图图层 (需切图资源):")
        for img in image_layers:
            lines.append(f"  \"{img['name']}\" ({img['path']})")
            lines.append(f"    位置: ({img['x']},{img['y']}) {img['w']}x{img['h']}")
            if img['opacity'] is not None:
                lines.append(f"    opacity: {img['opacity']}%")

    color_set = set()
    font_set = set()
    for t in text_layers:
        if t['color']:
            color_set.add(t['color'])
        if t['font']:
            font_set.add(t['font'])
        if t['fontSize']:
            font_set.add(f"{t['fontSize']}px")
    for s in shape_layers:
        if s['fill']:
            color_set.add(s['fill'])

    if color_set or font_set:
        lines.append("")
        lines.append("🎨 设计汇总:")
        if color_set:
            lines.append(f"  使用颜色: {', '.join(sorted(color_set))}")
        if font_set:
            lines.append(f"  字体/字号: {', '.join(sorted(font_set))}")

    lines.append("")
    lines.append("=" * 60)

    return '\n'.join(lines)


def _minify_css(css: str) -> str:
    """压缩 CSS：去掉注释、折叠空白。"""
    css = re.sub(r'/\*[\s\S]*?\*/', '', css)
    css = re.sub(r'\s+', ' ', css)
    return css.strip()


def minify_html(html: str) -> str:
    """
    压缩 HTML+CSS
    用于减少返回体体积和 token 消耗。
    """
    try:
        import htmlmin
    except ImportError:
        return html
    # 先压缩 <style> 内 CSS（htmlmin 默认不压缩 style 内容）
    def replace_style(match):
        inner = _minify_css(match.group(1))
        return f'<style>\n{inner}\n</style>'
    html = re.sub(r'<style[^>]*>([\s\S]*?)</style>', replace_style, html, count=0)
    return htmlmin.minify(
        html,
        remove_comments=True,
        remove_empty_space=True,
    )


def _localize_image_urls(html_code: str, design_name: str) -> tuple[str, dict]:
    """
    将生成的 HTML 中的远程图片 URL 替换为本地路径占位符，并返回下载映射表。
    文件名优先使用 CSS 类名（img class 属性 / CSS 规则选择器），退而使用计数器。
    同一 URL 复用同一本地路径（相同图片不重复下载）。
    """
    url_to_localpath: dict[str, str] = {}  # remote_url -> local_path, dedup
    url_mapping: dict[str, str] = {}       # local_path -> remote_url
    used_names: set[str] = set()
    counter = [0]

    def _get_ext(remote_url: str) -> str:
        path = urlparse(remote_url).path
        if '.' in path.split('/')[-1]:
            ext = '.' + path.split('/')[-1].rsplit('.', 1)[-1]
            if ext in ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'):
                return ext
        return '.png'

    def _sanitize(name: str) -> str:
        """去除循环后缀（-0/-1/...），保留主类名。"""
        return re.sub(r'-\d+$', '', name)

    def _unique_name(base: str, ext: str) -> str:
        candidate = f"{base}{ext}"
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate
        i = 2
        while True:
            candidate = f"{base}_{i}{ext}"
            if candidate not in used_names:
                used_names.add(candidate)
                return candidate
            i += 1

    def _get_localpath(remote_url: str, hint_class: str = None) -> str:
        if remote_url in url_to_localpath:
            return url_to_localpath[remote_url]
        ext = _get_ext(remote_url)
        if hint_class:
            base = _sanitize(hint_class)
        else:
            counter[0] += 1
            base = f"img_{counter[0]}"
        name = _unique_name(base, ext)
        local_path = f"./assets/slices/{name}"
        url_mapping[local_path] = remote_url
        url_to_localpath[remote_url] = local_path
        return local_path

    # Step 1: 从 CSS 规则中收集 url -> class_name 映射
    # 格式：.classname { ... background: url(https://...) ... }
    url_to_css_class: dict[str, str] = {}
    css_block = re.search(r'<style>(.*?)</style>', html_code, re.DOTALL)
    if css_block:
        for rule_m in re.finditer(r'\.([\w-]+)\s*\{([^}]*)\}', css_block.group(1), re.DOTALL):
            cls = rule_m.group(1)
            for url_m in re.finditer(r'url\([\'"]?(https?://[^\'") ]+)[\'"]?', rule_m.group(2)):
                url_to_css_class.setdefault(url_m.group(1), cls)

    # Step 2: 替换 <img src="...">，优先用 img 的 class 属性
    def _replace_img_tag(tag_match):
        tag = tag_match.group(0)
        src_m = re.search(r'src=["\']?(https?://[^"\'>\s]+)["\']?', tag)
        if not src_m:
            return tag
        url = src_m.group(1)
        cls_m = re.search(r'class=["\']([^"\']+)["\']', tag) or re.search(r'class=([^"\'>\s]+)', tag)
        hint = cls_m.group(1).split()[0] if cls_m else url_to_css_class.get(url)
        local_path = _get_localpath(url, hint)
        return tag[:src_m.start(1) - tag_match.start()] + local_path + tag[src_m.end(1) - tag_match.start():]

    # 先整体替换 <img> 标签（以保留 class 上下文）
    result = re.sub(r'<img\b[^>]*>', _replace_img_tag, html_code)

    # Step 3: 替换 CSS url(...) 背景图，用 CSS 类名作文件名
    def _replace_css_url(match):
        url = match.group(1).strip('\'"')
        if not url or not url.startswith('http'):
            return match.group(0)
        hint = url_to_css_class.get(url)
        local_path = _get_localpath(url, hint)
        return f"url('{local_path}')"

    result = re.sub(r'url\(([\'"]*https?://[^\)]*)\)', _replace_css_url, result)

    return result, url_mapping


# ==================== 转换器结束 ====================


def normalize_role(role: str) -> str:
    """
    将用户角色归一化到标准角色组
    
    Args:
        role: 用户原始角色名（如 "php后端"、"iOS开发"）
    
    Returns:
        标准角色名（如 "后端"、"客户端"）
    """
    if not role:
        return "未知"
    
    role_lower = role.lower()
    
    # 如果已经是标准角色，直接返回
    if role in VALID_ROLES:
        return role
    
    # 按规则匹配
    for keywords, standard_role in ROLE_MAPPING_RULES:
        for keyword in keywords:
            if keyword.lower() in role_lower:
                return standard_role
    
    # 无法匹配，返回原值
    return role


def _get_metadata_cache_key(project_id: str, doc_id: str = None) -> str:
    """生成元数据缓存键（不含版本号，用于查找）"""
    if doc_id:
        return f"{project_id}_{doc_id}"
    return project_id


def _get_cached_metadata(cache_key: str, version_id: str = None) -> Optional[dict]:
    """
    获取缓存的元数据
    
    Args:
        cache_key: 缓存键
        version_id: 文档版本ID，如果提供则检查版本是否匹配
    
    Returns:
        缓存的元数据，如果未命中或版本不匹配则返回None
    """
    if cache_key in _metadata_cache:
        cache_entry = _metadata_cache[cache_key]
        
        # 如果提供了version_id，检查版本是否匹配
        if version_id:
            if cache_entry.get('version_id') == version_id:
                return cache_entry['data']
            else:
                # 版本不匹配，删除旧缓存
                del _metadata_cache[cache_key]
                return None
        
        # 没有version_id，直接返回缓存（用于项目级别缓存）
        return cache_entry['data']
    
    return None


def _set_cached_metadata(cache_key: str, metadata: dict, version_id: str = None):
    """
    设置缓存（基于版本号的永久缓存）
    
    Args:
        cache_key: 缓存键
        metadata: 元数据
        version_id: 文档版本ID，存储后只要版本不变就永久有效
    """
    _metadata_cache[cache_key] = {
        'data': metadata.copy(),
        'version_id': version_id  # 版本号作为缓存有效性标识
    }


# ============================================
# 飞书机器人通知功能
# ============================================

async def send_feishu_notification(
    summary: str,
    content: str,
    author_name: str,
    author_role: str,
    mentions: List[str],
    message_type: str,
    project_name: str = None,
    doc_name: str = None,
    doc_url: str = None
) -> bool:
    """
    发送飞书机器人通知
    
    Args:
        summary: 留言标题
        content: 留言内容
        author_name: 作者名称
        author_role: 作者角色
        mentions: @的人名列表（必须是具体的人名，不能是角色）
        message_type: 消息类型
        project_name: 项目名称
        doc_name: 文档名称
        doc_url: 文档链接
    
    Returns:
        bool: 发送成功返回True，失败返回False
    """
    if not mentions:
        return False  # 没有@任何人，不发送通知
    
    # 消息类型emoji映射
    type_emoji = {
        "normal": "📢",
        "task": "📋",
        "question": "❓",
        "urgent": "🚨",
        "knowledge": "💡"
    }
    
    emoji = type_emoji.get(message_type, "📝")
    
    # 构建飞书@用户信息
    at_user_ids = []
    mention_names = []
    for name in mentions:
        user_id = FEISHU_USER_ID_MAP.get(name)
        if user_id:
            at_user_ids.append(user_id)
            mention_names.append(name)
    
    # 递归提取纯文本内容
    def extract_text(obj):
        """递归提取JSON中的纯文本"""
        if isinstance(obj, str):
            # 尝试解析字符串是否为JSON
            try:
                parsed = json.loads(obj)
                return extract_text(parsed)
            except:
                return obj
        elif isinstance(obj, list):
            texts = []
            for item in obj:
                text = extract_text(item)
                if text:
                    texts.append(text)
            return " ".join(texts)
        elif isinstance(obj, dict):
            # 提取text字段
            if "text" in obj:
                return extract_text(obj["text"])
            return ""
        else:
            return str(obj) if obj else ""
    
    plain_content = extract_text(content)
    
    # 限制内容长度
    if len(plain_content) > 500:
        plain_content = plain_content[:500] + "..."
    
    # 构建富文本内容（使用飞书post格式支持@功能）
    content_list = [
        # 发布者信息
        [{"tag": "text", "text": f"👤 发布者：{author_name}（{author_role}）\n"}],
        # 类型
        [{"tag": "text", "text": f"🏷️ 类型：{message_type}\n"}],
    ]
    
    # @提醒行（如果有@的人）
    if at_user_ids:
        mention_line = [{"tag": "text", "text": "📨 提醒："}]
        for user_id, name in zip(at_user_ids, mention_names):
            mention_line.append({"tag": "at", "user_id": user_id})
            mention_line.append({"tag": "text", "text": " "})
        mention_line.append({"tag": "text", "text": "\n"})
        content_list.append(mention_line)
    
    # 项目信息
    if project_name:
        content_list.append([{"tag": "text", "text": f"📁 项目：{project_name}\n"}])
    if doc_name:
        content_list.append([{"tag": "text", "text": f"📄 文档：{doc_name}\n"}])
    
    # 内容
    content_list.append([{"tag": "text", "text": f"\n📝 内容：\n{plain_content}\n"}])
    
    # 链接
    if doc_url:
        content_list.append([
            {"tag": "text", "text": "\n🔗 "},
            {"tag": "a", "text": "查看需求文档", "href": doc_url}
        ])
    
    # 飞书消息payload（使用富文本post格式）
    payload = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": summary,  # 直接使用summary，不再添加emoji（用户自己会加）
                    "content": content_list
                }
            }
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.post(
                FEISHU_WEBHOOK_URL,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            result = response.json()
            
            # 飞书成功响应: {"code":0,"msg":"success"}
            if result.get("code") == 0:
                if mention_names:
                    print(f"✅ 飞书通知发送成功: {summary} @{','.join(mention_names)}")
                else:
                    print(f"✅ 飞书通知发送成功: {summary}")
                return True
            else:
                print(f"⚠️ 飞书通知发送失败: {result}")
                return False
                
    except Exception as e:
        print(f"❌ 飞书通知发送异常: {e}")
        return False


# ============================================
# 消息存储类
# ============================================

class MessageStore:
    """消息存储管理类 - 支持团队留言板功能"""
    
    def __init__(self, project_id: str = None):
        """
        初始化消息存储
        
        Args:
            project_id: 项目ID，如果为None则用于全局操作模式
        """
        self.project_id = project_id
        self.storage_dir = DATA_DIR / "messages"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        if project_id:
            self.file_path = self.storage_dir / f"{project_id}.json"
            self._data = self._load()
        else:
            # 全局模式，不加载单个文件
            self.file_path = None
            self._data = None
    
    def _load(self) -> dict:
        """加载项目数据"""
        if self.file_path.exists():
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "project_id": self.project_id,
            "next_id": 1,
            "messages": [],
            "collaborators": []
        }
    
    def _save(self):
        """保存项目数据"""
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)
    
    def _get_now(self) -> str:
        """获取当前时间字符串（东八区/北京时间）"""
        return datetime.now(CHINA_TZ).strftime("%Y-%m-%d %H:%M:%S")
    
    def _check_mentions_me(self, mentions: List[str], user_role: str) -> bool:
        """检查消息是否@了当前用户（支持角色归一化匹配）"""
        if not mentions:
            return False
        if "所有人" in mentions:
            return True
        
        # 将用户角色归一化后匹配
        normalized_user_role = normalize_role(user_role)
        
        # 直接匹配原始角色
        if user_role in mentions:
            return True
        
        # 匹配归一化后的角色
        if normalized_user_role in mentions:
            return True
        
        return False
    
    def record_collaborator(self, name: str, role: str):
        """记录/更新协作者"""
        if not name or not role:
            return
        
        now = self._get_now()
        collaborators = self._data.get("collaborators", [])
        
        # 查找是否已存在
        for collab in collaborators:
            if collab["name"] == name and collab["role"] == role:
                collab["last_seen"] = now
                self._save()
                return
        
        # 新增协作者
        collaborators.append({
            "name": name,
            "role": role,
            "first_seen": now,
            "last_seen": now
        })
        self._data["collaborators"] = collaborators
        self._save()
    
    def get_collaborators(self) -> List[dict]:
        """获取协作者列表"""
        return self._data.get("collaborators", [])
    
    def save_message(self, summary: str, content: str, author_name: str, 
                     author_role: str, mentions: List[str] = None,
                     message_type: str = 'normal',
                     project_name: str = None, folder_name: str = None,
                     doc_id: str = None, doc_name: str = None,
                     doc_type: str = None, doc_version: str = None,
                     doc_updated_at: str = None, doc_url: str = None) -> dict:
        """
        保存新消息（包含标准元数据）
        
        Args:
            summary: 消息概要
            content: 消息内容
            author_name: 作者名称
            author_role: 作者角色
            mentions: @的角色列表
            message_type: 留言类型 (normal/task/question/urgent)
            project_name: 项目名称
            folder_name: 文件夹名称
            doc_id: 文档ID
            doc_name: 文档名称
            doc_type: 文档类型
            doc_version: 文档版本
            doc_updated_at: 文档更新时间
            doc_url: 文档URL
        """
        msg_id = self._data["next_id"]
        self._data["next_id"] += 1
        
        now = self._get_now()
        message = {
            "id": msg_id,
            "summary": summary,
            "content": content,
            "mentions": mentions or [],
            "message_type": message_type,  # 新增：留言类型
            "author_name": author_name,
            "author_role": author_role,
            "created_at": now,
            "updated_at": None,
            "updated_by_name": None,
            "updated_by_role": None,
            
            # 标准元数据（10个字段）
            "project_id": self.project_id,
            "project_name": project_name,
            "folder_name": folder_name,
            "doc_id": doc_id,
            "doc_name": doc_name,
            "doc_type": doc_type,
            "doc_version": doc_version,
            "doc_updated_at": doc_updated_at,
            "doc_url": doc_url
        }
        
        self._data["messages"].append(message)
        self._save()
        return message
    
    def get_messages(self, user_role: str = None) -> List[dict]:
        """获取所有消息（不含content，用于列表展示）"""
        messages = []
        for msg in self._data.get("messages", []):
            msg_copy = {k: v for k, v in msg.items() if k != "content"}
            if user_role:
                msg_copy["mentions_me"] = self._check_mentions_me(msg.get("mentions", []), user_role)
            messages.append(msg_copy)
        # 按创建时间倒序排列
        messages.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return messages
    
    def get_message_by_id(self, msg_id: int, user_role: str = None) -> Optional[dict]:
        """根据ID获取消息（含content）"""
        for msg in self._data.get("messages", []):
            if msg["id"] == msg_id:
                msg_copy = msg.copy()
                if user_role:
                    msg_copy["mentions_me"] = self._check_mentions_me(msg.get("mentions", []), user_role)
                return msg_copy
        return None
    
    def update_message(self, msg_id: int, editor_name: str, editor_role: str,
                       summary: str = None, content: str = None, 
                       mentions: List[str] = None) -> Optional[dict]:
        """更新消息"""
        for msg in self._data.get("messages", []):
            if msg["id"] == msg_id:
                if summary is not None:
                    msg["summary"] = summary
                if content is not None:
                    msg["content"] = content
                if mentions is not None:
                    msg["mentions"] = mentions
                msg["updated_at"] = self._get_now()
                msg["updated_by_name"] = editor_name
                msg["updated_by_role"] = editor_role
                self._save()
                return msg
        return None
    
    def delete_message(self, msg_id: int) -> bool:
        """删除消息"""
        messages = self._data.get("messages", [])
        for i, msg in enumerate(messages):
            if msg["id"] == msg_id:
                messages.pop(i)
                self._save()
                return True
        return False
    
    def get_all_messages(self, user_role: str = None) -> List[dict]:
        """
        获取所有项目的留言（全局查询）
        
        Args:
            user_role: 用户角色，用于判断是否@了该用户
        
        Returns:
            包含所有项目消息的列表（已排序）
        """
        all_messages = []
        
        # 遍历所有JSON文件
        for json_file in self.storage_dir.glob("*.json"):
            project_id = json_file.stem
            try:
                project_store = MessageStore(project_id)
                messages = project_store.get_messages(user_role=user_role)
                
                # 消息中已包含元数据，直接添加
                all_messages.extend(messages)
            except Exception:
                # 某个项目加载失败不影响其他项目
                continue
        
        # 全局排序（按创建时间倒序）
        all_messages.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return all_messages
    
    def get_all_messages_grouped(self, user_role: str = None, user_name: str = None) -> List[dict]:
        """
        获取所有项目的留言（分组返回，节省token）
        
        按项目+文档分组，每组的元数据只出现一次，避免重复
        
        Args:
            user_role: 用户角色，用于判断是否@了该用户
            user_name: 用户名，用于判断消息是否是自己发的
        
        Returns:
            分组列表，每组包含元数据和该组的消息
        """
        # 先获取所有消息
        all_messages = self.get_all_messages(user_role)
        
        # 按 (project_id, doc_id) 分组
        from collections import defaultdict
        groups_dict = defaultdict(list)
        
        for msg in all_messages:
            # 生成分组键
            project_id = msg.get('project_id', 'unknown')
            doc_id = msg.get('doc_id', 'no_doc')
            group_key = f"{project_id}_{doc_id}"
            
            groups_dict[group_key].append(msg)
        
        # 构建分组结果
        groups = []
        for group_key, messages in groups_dict.items():
            if not messages:
                continue
            
            # 从第一条消息中提取元数据（组内共享）
            first_msg = messages[0]
            
            # 构建组信息
            group = {
                # 元数据（只出现一次）
                "project_id": first_msg.get('project_id'),
                "project_name": first_msg.get('project_name'),
                "folder_name": first_msg.get('folder_name'),
                "doc_id": first_msg.get('doc_id'),
                "doc_name": first_msg.get('doc_name'),
                "doc_type": first_msg.get('doc_type'),
                "doc_version": first_msg.get('doc_version'),
                "doc_updated_at": first_msg.get('doc_updated_at'),
                "doc_url": first_msg.get('doc_url'),
                
                # 统计信息
                "message_count": len(messages),
                "mentions_me_count": sum(1 for m in messages if m.get("mentions_me")),
                
                # 消息列表（移除元数据字段）
                "messages": []
            }
            
            # 移除消息中的元数据字段，只保留核心信息
            meta_fields = {
                'project_id', 'project_name', 'folder_name',
                'doc_id', 'doc_name', 'doc_type', 'doc_version',
                'doc_updated_at', 'doc_url'
            }
            
            for msg in messages:
                # 创建精简消息（不含元数据）
                slim_msg = {k: v for k, v in msg.items() if k not in meta_fields}
                # 清理null字段并添加is_edited/is_mine标志
                slim_msg = _clean_message_dict(slim_msg, user_name)
                group["messages"].append(slim_msg)
            
            groups.append(group)
        
        # 按组内最新消息时间排序
        groups.sort(
            key=lambda g: max((m.get('created_at', '') for m in g['messages']), default=''),
            reverse=True
        )
        
        return groups



def get_user_info(ctx: Context) -> tuple:
    """
    从URL query参数获取用户信息
    
    MCP连接URL格式：http://xxx:port/mcp?role=后端&name=张三
    """
    try:
        # 使用 FastMCP 提供的 get_http_request 获取当前请求
        from fastmcp.server.dependencies import get_http_request
        req = get_http_request()
        
        # 从 query 参数获取
        name = req.query_params.get('name', '匿名')
        role = req.query_params.get('role', '未知')
        return name, role
    except Exception:
        pass
    return '匿名', '未知'


def _clean_message_dict(msg: dict, current_user_name: str = None) -> dict:
    """
    清理消息字典，移除null值的更新字段，并添加快捷标志
    
    优化：
    1. 如果消息未被编辑，省略 updated_at/updated_by_name/updated_by_role
    2. 添加 is_edited 标志
    3. 添加 is_mine 标志（如果提供了current_user_name）
    """
    cleaned = msg.copy()
    
    # 如果消息未被编辑，省略这些字段
    if cleaned.get('updated_at') is None:
        cleaned.pop('updated_at', None)
        cleaned.pop('updated_by_name', None)
        cleaned.pop('updated_by_role', None)
        cleaned['is_edited'] = False
    else:
        cleaned['is_edited'] = True
    
    # 添加is_mine标志
    if current_user_name:
        cleaned['is_mine'] = (cleaned.get('author_name') == current_user_name)
    
    return cleaned


def get_project_id_from_url(url: str) -> str:
    """从URL中提取project_id"""
    if not url or url.lower() == 'all':
        return None
    extractor = LanhuExtractor()
    params = extractor.parse_url(url)
    return params.get('project_id', '')


async def _fetch_metadata_from_url(url: str) -> dict:
    """
    从蓝湖URL获取标准元数据（10个字段）- 支持基于版本号的永久缓存
    
    Args:
        url: 蓝湖URL
    
    Returns:
        包含10个元数据字段的字典，获取失败的字段为None
    """
    metadata = {
        'project_id': None,
        'project_name': None,
        'folder_name': None,
        'doc_id': None,
        'doc_name': None,
        'doc_type': None,
        'doc_version': None,
        'doc_updated_at': None,
        'doc_url': None
    }
    
    extractor = LanhuExtractor()
    try:
        params = extractor.parse_url(url)
        project_id = params.get('project_id')
        doc_id = params.get('doc_id')
        team_id = params.get('team_id')
        
        metadata['project_id'] = project_id
        metadata['doc_id'] = doc_id
        
        if not project_id:
            return metadata
        
        # 生成缓存键
        cache_key = _get_metadata_cache_key(project_id, doc_id)
        
        # 如果有doc_id，获取文档信息和版本号
        version_id = None
        if doc_id:
            doc_info = await extractor.get_document_info(project_id, doc_id)
            
            # 获取版本ID
            versions = doc_info.get('versions', [])
            if versions:
                version_id = versions[0].get('id')
                metadata['doc_version'] = versions[0].get('version_info')
            
            # 检查缓存（基于版本号）
            cached = _get_cached_metadata(cache_key, version_id)
            if cached:
                return cached
            
            # 缓存未命中，继续获取数据
            metadata['doc_name'] = doc_info.get('name')
            metadata['doc_type'] = doc_info.get('type', 'axure')
            
            # 格式化更新时间
            update_time = doc_info.get('update_time')
            if update_time:
                try:
                    dt = datetime.fromisoformat(update_time.replace('Z', '+00:00'))
                    dt_china = dt.astimezone(CHINA_TZ)
                    metadata['doc_updated_at'] = dt_china.strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    metadata['doc_updated_at'] = update_time
            
            # 构建文档URL
            if team_id and project_id and doc_id:
                metadata['doc_url'] = (
                    f"https://lanhuapp.com/web/#/item/project/product"
                    f"?tid={team_id}&pid={project_id}&docId={doc_id}"
                )
        
        # 获取项目信息
        if project_id and team_id:
            try:
                response = await extractor.client.get(
                    f"{BASE_URL}/api/project/multi_info",
                    params={
                        'project_id': project_id,
                        'team_id': team_id,
                        'doc_info': 1
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get('code') == '00000':
                        project_info = data.get('result', {})
                        metadata['project_name'] = project_info.get('name')
                        metadata['folder_name'] = project_info.get('folder_name')
            except Exception:
                pass
        
        # 存入缓存（基于版本号）
        _set_cached_metadata(cache_key, metadata, version_id)
    
    except Exception:
        pass
    finally:
        await extractor.close()
    
    return metadata



class LanhuExtractor:
    """蓝湖提取器"""

    CACHE_META_FILE = ".lanhu_cache.json"  # 缓存元数据文件名

    def __init__(self):
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://lanhuapp.com/web/",
            "Accept": "application/json, text/plain, */*",
            "Cookie": COOKIE,
            "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "request-from": "web",
            "real-path": "/item/project/product"
        }
        self.client = httpx.AsyncClient(timeout=HTTP_TIMEOUT, headers=headers, follow_redirects=True)

    def parse_url(self, url: str) -> dict:
        """
        解析蓝湖URL，支持多种格式：
        1. 完整URL: https://lanhuapp.com/web/#/item/project/product?tid=...&pid=...
        2. 完整URL: https://lanhuapp.com/web/#/item/project/stage?tid=...&pid=...
        3. 参数部分: ?tid=...&pid=...
        4. 参数部分（无?）: tid=...&pid=...

        Args:
            url: 蓝湖URL或参数字符串

        Returns:
            包含project_id, team_id, doc_id, version_id的字典
        """
        # 如果是完整URL，提取fragment部分
        if url.startswith('http'):
            parsed = urlparse(url)
            fragment = parsed.fragment

            if not fragment:
                raise ValueError("Invalid Lanhu URL: missing fragment part")

            # 从fragment中提取参数部分
            if '?' in fragment:
                url = fragment.split('?', 1)[1]
            else:
                url = fragment

        # 处理只有参数的情况
        if url.startswith('?'):
            url = url[1:]

        # 解析参数
        params = {}
        for part in url.split('&'):
            if '=' in part:
                key, value = part.split('=', 1)
                params[key] = value

        # 提取必需参数
        team_id = params.get('tid')
        project_id = params.get('pid')
        doc_id = params.get('docId') or params.get('image_id')
        version_id = params.get('versionId')

        # 验证必需参数
        if not project_id:
            raise ValueError(f"URL parsing failed: missing required param pid (project_id)")

        if not team_id:
            raise ValueError(f"URL parsing failed: missing required param tid (team_id)")

        return {
            'team_id': team_id,
            'project_id': project_id,
            'doc_id': doc_id,
            'version_id': version_id
        }

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

    def _get_cache_meta_path(self, output_dir: Path) -> Path:
        """获取缓存元数据文件路径"""
        return output_dir / self.CACHE_META_FILE

    def _load_cache_meta(self, output_dir: Path) -> dict:
        """加载缓存元数据"""
        meta_path = self._get_cache_meta_path(output_dir)
        if meta_path.exists():
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cache_meta(self, output_dir: Path, meta_data: dict):
        """保存缓存元数据"""
        meta_path = self._get_cache_meta_path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(meta_data, f, ensure_ascii=False, indent=2)

    def _check_file_integrity(self, output_dir: Path, expected_files: dict) -> dict:
        """
        检查文件完整性

        Args:
            output_dir: 输出目录
            expected_files: 期望的文件字典 {相对路径: md5签名}

        Returns:
            {
                'missing': [缺失的文件列表],
                'corrupted': [损坏的文件列表],
                'valid': [有效的文件列表]
            }
        """
        result = {
            'missing': [],
            'corrupted': [],
            'valid': []
        }

        for rel_path, expected_md5 in expected_files.items():
            file_path = output_dir / rel_path

            if not file_path.exists():
                result['missing'].append(rel_path)
            elif expected_md5:
                # 如果有MD5签名，验证文件
                # 注意：这里简化处理，只检查文件是否存在
                # 完整的MD5验证会比较慢
                result['valid'].append(rel_path)
            else:
                result['valid'].append(rel_path)

        return result

    def _should_update_cache(self, output_dir: Path, current_version_id: str, project_mapping: dict) -> tuple:
        """
        检查是否需要更新缓存

        Returns:
            (需要更新, 缺失的文件列表)
        """
        cache_meta = self._load_cache_meta(output_dir)

        # 检查版本
        cached_version = cache_meta.get('version_id')
        if cached_version != current_version_id:
            return (True, 'version_changed', [])

        # 检查文件完整性
        pages = project_mapping.get('pages', {})
        expected_files = {}

        # 收集所有应该存在的文件
        for html_filename in pages.keys():
            expected_files[html_filename] = None

        # 检查关键目录
        for key_dir in ['data', 'resources', 'files', 'images']:
            expected_files[key_dir] = None

        integrity = self._check_file_integrity(output_dir, expected_files)

        if integrity['missing']:
            return (True, 'files_missing', integrity['missing'])

        return (False, 'up_to_date', [])

    async def get_pages_list(self, url: str) -> dict:
        """获取文档的所有页面列表（仅包含sitemap中的页面，与Web界面一致）"""
        params = self.parse_url(url)
        doc_info = await self.get_document_info(params['project_id'], params['doc_id'])

        # 获取项目详细信息（包含创建者等信息）
        project_info = None
        try:
            response = await self.client.get(
                f"{BASE_URL}/api/project/multi_info",
                params={
                    'project_id': params['project_id'],
                    'team_id': params['team_id'],
                    'doc_info': 1
                }
            )
            response.raise_for_status()
            data = response.json()
            if data.get('code') == '00000':
                project_info = data.get('result', {})
        except Exception:
            pass  # 如果获取失败，继续使用基本信息

        # 获取项目级mapping JSON
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

        # 从sitemap获取页面列表（只返回在导航中显示的页面）
        sitemap = project_mapping.get('sitemap', {})
        root_nodes = sitemap.get('rootNodes', [])

        # 递归提取所有页面（保留层级结构）
        def extract_pages(nodes, pages_list, parent_path="", level=0, parent_folder=None):
            """
            递归提取页面，保留层级信息
            
            根据真实蓝湖sitemap结构：
            - 纯文件夹：type="Folder" 且 url=""
            - 页面节点：有url字段（type="Wireframe"等）
            - 页面可以有children（子页面）
            
            Args:
                nodes: 当前层级的节点列表
                pages_list: 输出的页面列表
                parent_path: 父级路径（用/分隔）
                level: 当前层级深度（0为根）
                parent_folder: 所属文件夹名称（最近的Folder节点）
            """
            for node in nodes:
                page_name = node.get('pageName', '')
                url = node.get('url', '')
                node_type = node.get('type', 'Wireframe')
                node_id = node.get('id', '')
                
                # 构建当前路径
                current_path = f"{parent_path}/{page_name}" if parent_path else page_name
                
                # 判断是否为纯文件夹（type=Folder 且 无url）
                is_pure_folder = (node_type == 'Folder' and not url)
                
                if page_name and url:
                    # 这是一个页面（有url的都是页面）
                    pages_list.append({
                        'index': len(pages_list) + 1,
                        'name': page_name,
                        'filename': url,
                        'id': node_id,
                        'type': node_type,
                        'level': level,
                        'folder': parent_folder or '根目录',  # 所属文件夹
                        'path': current_path,  # 完整路径
                        'has_children': bool(node.get('children'))  # 是否有子页面
                    })
                
                # 递归处理子节点
                children = node.get('children', [])
                if children:
                    # 如果当前是纯文件夹，更新parent_folder
                    # 如果当前是页面，保持原parent_folder
                    next_folder = page_name if is_pure_folder else parent_folder
                    
                    extract_pages(
                        children, 
                        pages_list, 
                        parent_path=current_path,
                        level=level + 1,
                        parent_folder=next_folder
                    )

        pages_list = []
        extract_pages(root_nodes, pages_list)

        # 格式化时间（转换为东八区/北京时间）
        def format_time(time_str):
            if not time_str:
                return None
            try:
                # 处理ISO格式时间，转换为东八区
                dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                dt_china = dt.astimezone(CHINA_TZ)
                return dt_china.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                return time_str

        # 统计分组信息
        from collections import defaultdict
        folder_stats = defaultdict(int)
        max_level = 0
        pages_with_children = 0
        
        for page in pages_list:
            folder = page.get('folder', '根目录')
            folder_stats[folder] += 1
            max_level = max(max_level, page.get('level', 0))
            if page.get('has_children'):
                pages_with_children += 1
        
        # 构建返回结果
        result = {
            'document_id': params['doc_id'],
            'document_name': doc_info.get('name', 'Unknown'),
            'document_type': doc_info.get('type', 'axure'),
            'total_pages': len(pages_list),
            'max_level': max_level,
            'pages_with_children': pages_with_children,  # 有子页面的页面数
            'folder_statistics': dict(folder_stats),  # 每个文件夹下有多少页面（按纯Folder统计）
            'pages': pages_list
        }

        # 添加时间信息
        if doc_info.get('create_time'):
            result['create_time'] = format_time(doc_info.get('create_time'))
        if doc_info.get('update_time'):
            result['update_time'] = format_time(doc_info.get('update_time'))

        # 添加版本信息
        result['total_versions'] = len(versions)
        if latest_version.get('version_info'):
            result['latest_version'] = latest_version.get('version_info')

        # 添加项目信息（如果成功获取）
        if project_info:
            if project_info.get('creator_name'):
                result['creator_name'] = project_info.get('creator_name')
            if project_info.get('folder_name'):
                result['folder_name'] = project_info.get('folder_name')
            if project_info.get('save_path'):
                result['project_path'] = project_info.get('save_path')
            if project_info.get('member_cnt'):
                result['member_count'] = project_info.get('member_cnt')

        return result

    async def download_resources(self, url: str, output_dir: str, force_update: bool = False) -> dict:
        """
        下载所有Axure资源（支持智能缓存）

        Args:
            url: 蓝湖文档URL
            output_dir: 输出目录
            force_update: 强制更新，忽略缓存

        Returns:
            {
                'status': 'downloaded' | 'cached' | 'updated',
                'version_id': 版本ID,
                'reason': 更新原因,
                'output_dir': 输出目录
            }
        """
        params = self.parse_url(url)
        doc_info = await self.get_document_info(params['project_id'], params['doc_id'])

        # 获取项目级mapping JSON
        versions = doc_info.get('versions', [])
        version_info = versions[0]
        version_id = version_info.get('id', '')  # 版本ID字段名是'id'
        json_url = version_info.get('json_url')

        response = await self.client.get(json_url)
        response.raise_for_status()
        project_mapping = response.json()

        # 创建输出目录
        output_path = Path(output_dir)

        # 检查是否需要更新
        if not force_update and output_path.exists():
            need_update, reason, missing_files = self._should_update_cache(
                output_path, version_id, project_mapping
            )

            if not need_update:
                return {
                    'status': 'cached',
                    'version_id': version_id,
                    'reason': reason,
                    'output_dir': output_dir
                }

            # 如果只是文件缺失，可以增量下载
            if reason == 'files_missing' and missing_files:
                # 这里可以实现增量下载逻辑
                # 为了简化，暂时还是全量下载
                pass

        output_path.mkdir(parents=True, exist_ok=True)

        # 下载每个页面的资源
        pages = project_mapping.get('pages', {})
        is_first_page = True

        downloaded_files = []

        for html_filename, page_info in pages.items():
            html_data = page_info.get('html', {})
            html_file_with_md5 = html_data.get('sign_md5', '')
            page_mapping_md5 = page_info.get('mapping_md5', '')

            if not html_file_with_md5:
                continue

            # 下载HTML
            html_url = f"{CDN_URL}/{html_file_with_md5}"
            response = await self.client.get(html_url)
            response.raise_for_status()
            html_content = response.text

            # 下载页面级mapping JSON
            if page_mapping_md5:
                mapping_url = f"{CDN_URL}/{page_mapping_md5}"
                response = await self.client.get(mapping_url)
                response.raise_for_status()
                page_mapping = response.json()

                # 下载所有依赖资源
                await self._download_page_resources(
                    page_mapping, output_path, skip_document_js=(not is_first_page)
                )
                is_first_page = False

            # 保存HTML
            html_path = output_path / html_filename
            html_path.write_text(html_content, encoding='utf-8')
            downloaded_files.append(html_filename)

        # 保存缓存元数据
        cache_meta = {
            'version_id': version_id,
            'document_id': params['doc_id'],
            'document_name': doc_info.get('name', 'Unknown'),
            'download_time': asyncio.get_event_loop().time(),
            'pages': list(pages.keys()),
            'total_files': len(downloaded_files)
        }
        self._save_cache_meta(output_path, cache_meta)

        return {
            'status': 'downloaded',
            'version_id': version_id,
            'reason': 'first_download' if not output_path.exists() else 'version_changed',
            'output_dir': output_dir
        }

    async def _download_page_resources(self, page_mapping: dict, output_dir: Path, skip_document_js: bool = False):
        """下载页面资源"""
        tasks = []

        # 下载CSS
        for local_path, info in page_mapping.get('styles', {}).items():
            sign_md5 = info.get('sign_md5', '')
            if sign_md5:
                url = sign_md5 if sign_md5.startswith('http') else f"{CDN_URL}/{sign_md5}"
                tasks.append(self._download_file(url, output_dir / local_path))

        # 下载JS
        for local_path, info in page_mapping.get('scripts', {}).items():
            if skip_document_js and local_path == 'data/document.js':
                continue
            sign_md5 = info.get('sign_md5', '')
            if sign_md5:
                url = sign_md5 if sign_md5.startswith('http') else f"{CDN_URL}/{sign_md5}"
                tasks.append(self._download_file(url, output_dir / local_path))

        # 下载图片
        for local_path, info in page_mapping.get('images', {}).items():
            sign_md5 = info.get('sign_md5', '')
            if sign_md5:
                url = sign_md5 if sign_md5.startswith('http') else f"{CDN_URL}/{sign_md5}"
                tasks.append(self._download_file(url, output_dir / local_path))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _download_file(self, url: str, local_path: Path):
        """下载单个文件"""
        try:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            response = await self.client.get(url)
            response.raise_for_status()
            local_path.write_bytes(response.content)
        except Exception:
            pass

    @staticmethod
    def _build_scale_urls(image_url: str, logical_w: float, logical_h: float, slice_scale: int) -> dict:
        """
        生成多倍图下载 URL（OSS image/resize 参数）。

        蓝湖切图只存一张图（stored = logical × sliceScale，通常 2x）。
        不同倍率通过 OSS x-oss-process=image/resize 实现在线裁剪。

        Args:
            image_url:   OSS 原图 URL（stored = logical × sliceScale）
            logical_w/h: 逻辑 1x 尺寸（来自 image.size.width/height 或 ddsImage.size）
            slice_scale: 切图导出倍率（sketch JSON 根节点 sliceScale，通常为 2）

        Returns:
            dict: 包含 1x/2x/3x 及各平台常用倍率的 URL
        """
        if not image_url or not logical_w or not logical_h:
            return {}

        lw = max(1, int(round(logical_w)))
        lh = max(1, int(round(logical_h)))
        stored_w = lw * slice_scale
        stored_h = lh * slice_scale

        def make_url(w: int, h: int) -> str:
            w, h = max(1, w), max(1, h)
            if w == stored_w and h == stored_h:
                return image_url  # 恰好是存储尺寸，无需 resize
            return f"{image_url}?x-oss-process=image/resize,w_{w},h_{h}/format,png"

        def js_round(v: float) -> int:
            """模拟 JavaScript Math.round（.5 向上取整）"""
            import math
            return math.floor(v + 0.5)

        # iOS 按 stored/4 基准（hardcoded by Lanhu frontend）
        ios_base = stored_w / 4
        return {
            # Web / 通用
            '1x': make_url(lw * 1, lh * 1),
            '2x': make_url(lw * 2, lh * 2),   # = stored，原图
            '3x': make_url(lw * 3, lh * 3),
            # iOS（@2x = Web @1x = logical size）
            'ios_1x':  make_url(max(1, js_round(ios_base * 1)), max(1, js_round(stored_h / 4 * 1))),
            'ios_2x':  make_url(max(1, js_round(ios_base * 2)), max(1, js_round(stored_h / 4 * 2))),
            'ios_3x':  make_url(max(1, js_round(ios_base * 3)), max(1, js_round(stored_h / 4 * 3))),
            # Android
            'android_mdpi':    make_url(max(1, js_round(stored_w / 4 * 1)),   max(1, js_round(stored_h / 4 * 1))),
            'android_hdpi':    make_url(max(1, js_round(stored_w / 4 * 1.5)), max(1, js_round(stored_h / 4 * 1.5))),
            'android_xhdpi':   make_url(max(1, js_round(stored_w / 4 * 2)),   max(1, js_round(stored_h / 4 * 2))),
            'android_xxhdpi':  make_url(max(1, js_round(stored_w / 4 * 3)),   max(1, js_round(stored_h / 4 * 3))),
            'android_xxxhdpi': make_url(stored_w, stored_h),               # = 原图
        }

    async def get_design_slices_info(self, image_id: str, team_id: str, project_id: str,
                                     include_metadata: bool = True) -> dict:
        """
        获取设计图的所有切图信息（仅返回元数据和下载地址，不下载文件）

        Args:
            image_id: 设计图ID
            team_id: 团队ID
            project_id: 项目ID
            include_metadata: 是否包含详细元数据（位置、颜色、样式等）

        Returns:
            包含切图列表和详细信息的字典
        """
        # 1. 获取设计图详情
        url = f"{BASE_URL}/api/project/image"
        params = {
            "dds_status": 1,
            "image_id": image_id,
            "team_id": team_id,
            "project_id": project_id
        }
        response = await self.client.get(url, params=params)
        data = response.json()

        if data['code'] != '00000':
            raise Exception(f"Failed to get design: {data['msg']}")

        result = data['result']
        latest_version = result['versions'][0]
        json_url = latest_version['json_url']

        # 2. 下载并解析Sketch JSON
        json_response = await self.client.get(json_url)
        sketch_data = json_response.json()

        # sliceScale：切图导出倍率（通常为 2，即存储尺寸 = 逻辑尺寸 × 2）
        # Figma JSON 将 sliceScale 存在 meta 子对象中
        meta = sketch_data.get('meta') or {}
        slice_scale = int(
            sketch_data.get('sliceScale') or
            sketch_data.get('exportScale') or
            meta.get('sliceScale') or
            2
        )
        # Figma 设计：bitmapLayer(hasExportImage=True) 才是真切图，shapeLayer 的 ddsImage 是图片填充层
        is_figma = (meta.get('host') or {}).get('name') == 'figma'

        # 3. 递归提取所有切图
        slices = []

        def find_slices(obj, parent_name="", layer_path=""):
            """
            递归查找切图，兼容新旧两种JSON结构

            Figma 结构:
            - 根节点: artboard.layers[]
            - 真切图: bitmapLayer + hasExportImage=True，字段 image.imageUrl
            - 图片填充（跳过）: shapeLayer/groupLayer + hasExportDDSImage=True，字段 ddsImage.imageUrl

            旧版 Sketch 结构:
            - 根节点: info[]
            - 切图字段: ddsImage.imageUrl
            """
            if not obj or not isinstance(obj, dict):
                return

            current_name = obj.get('name', '')
            current_path = f"{layer_path}/{current_name}" if layer_path else current_name

            # 检查 image 字段
            # Figma: bitmapLayer + hasExportImage=True 才是真切图，其余跳过
            if obj.get('image') and (obj['image'].get('imageUrl') or obj['image'].get('svgUrl')):
                if is_figma and not obj.get('hasExportImage'):
                    pass  # Figma 图片填充层，不是切图
                else:
                    image_data = obj['image']

                    # 优先使用PNG格式，如果没有则使用SVG
                    download_url = image_data.get('imageUrl') or image_data.get('svgUrl')

                    # 逻辑尺寸：image.size 是 1x 逻辑像素（stored = logical × sliceScale）
                    img_size = image_data.get('size') or {}
                    logical_w = img_size.get('width') or 0
                    logical_h = img_size.get('height') or 0

                    # frame fallback：Figma bitmapLayer 的 frame 已是逻辑像素（1x），直接用
                    if not logical_w or not logical_h:
                        frame = obj.get('frame') or obj.get('bounds') or {}
                        frame_w = frame.get('width', 0)
                        frame_h = frame.get('height', 0)
                        if frame_w:
                            logical_w = frame_w
                            logical_h = frame_h
                    size_str = f"{int(logical_w)}x{int(logical_h)}" if logical_w and logical_h else "unknown"

                    frame = obj.get('frame') or obj.get('bounds') or {}
                    slice_info = {
                        'id': obj.get('id'),
                        'name': current_name,
                        'type': obj.get('type') or obj.get('layerType') or 'bitmap',
                        'download_url': download_url,
                        'size': size_str,
                        'format': 'png' if image_data.get('imageUrl') else 'svg',
                    }

                    # SVG URL（Figma bitmapLayer 同时提供 SVG）
                    if image_data.get('svgUrl') and image_data.get('imageUrl'):
                        slice_info['svg_url'] = image_data['svgUrl']

                    # 多倍图 URL（1x/2x/3x 及各平台倍率）
                    if download_url and image_data.get('imageUrl'):
                        slice_info['scale_urls'] = self._build_scale_urls(
                            download_url, logical_w, logical_h, slice_scale
                        )
                        slice_info['logical_size'] = {
                            'width': int(logical_w),
                            'height': int(logical_h),
                            'note': f'1x logical px; stored at {slice_scale}x = {int(logical_w * slice_scale)}x{int(logical_h * slice_scale)}px'
                        }

                    # 添加位置信息
                    x = frame.get('x') or frame.get('left', 0)
                    y = frame.get('y') or frame.get('top', 0)
                    if x is not None or y is not None:
                        slice_info['position'] = {
                            'x': int(x),
                            'y': int(y)
                        }

                    # 添加父图层信息
                    if parent_name:
                        slice_info['parent_name'] = parent_name

                    slice_info['layer_path'] = current_path

                    # 如果需要详细元数据
                    if include_metadata:
                        metadata = {}

                        # 填充颜色
                        if obj.get('fills'):
                            metadata['fills'] = obj['fills']

                        # 边框
                        if obj.get('borders') or obj.get('strokes'):
                            metadata['borders'] = obj.get('borders') or obj.get('strokes')

                        # 透明度
                        if 'opacity' in obj:
                            metadata['opacity'] = obj['opacity']

                        # 旋转
                        if obj.get('rotation'):
                            metadata['rotation'] = obj['rotation']

                        # 文本样式
                        if obj.get('textStyle'):
                            metadata['text_style'] = obj['textStyle']

                        # 阴影
                        if obj.get('shadows'):
                            metadata['shadows'] = obj['shadows']

                        # 圆角
                        if obj.get('radius') or obj.get('cornerRadius'):
                            metadata['border_radius'] = obj.get('radius') or obj.get('cornerRadius')

                        if metadata:
                            slice_info['metadata'] = metadata

                    slices.append(slice_info)

            # 旧版结构: 检查 ddsImage 字段（Sketch 兼容；Figma 的 ddsImage 是图片填充层，不是切图）
            elif obj.get('ddsImage') and obj['ddsImage'].get('imageUrl') and not is_figma:
                dds = obj['ddsImage']
                dds_url = dds['imageUrl']
                dds_size = dds.get('size') or {}
                if isinstance(dds_size, dict):
                    logical_w = dds_size.get('width') or 0
                    logical_h = dds_size.get('height') or 0
                else:
                    logical_w = logical_h = 0

                # 旧版 Sketch: ddsImage.size 缺失时从 frame 兜底（frame 是逻辑像素）
                if not logical_w or not logical_h:
                    frame = obj.get('frame') or obj.get('bounds') or {}
                    frame_w = frame.get('width', 0)
                    frame_h = frame.get('height', 0)
                    if frame_w:
                        logical_w = frame_w
                        logical_h = frame_h

                size_str = f"{int(logical_w)}x{int(logical_h)}" if logical_w and logical_h else str(dds_size)

                slice_info = {
                    'id': obj.get('id'),
                    'name': current_name,
                    'type': obj.get('type') or obj.get('ddsType'),
                    'download_url': dds_url,
                    'size': size_str,
                    'format': 'png',
                }

                # 多倍图 URL
                if dds_url and logical_w:
                    slice_info['scale_urls'] = self._build_scale_urls(
                        dds_url, logical_w, logical_h, slice_scale
                    )
                    slice_info['logical_size'] = {
                        'width': int(logical_w),
                        'height': int(logical_h),
                        'note': f'1x logical px; stored at {slice_scale}x = {int(logical_w * slice_scale)}x{int(logical_h * slice_scale)}px'
                    }

                # 添加位置信息
                if 'left' in obj and 'top' in obj:
                    slice_info['position'] = {
                        'x': int(obj.get('left', 0)),
                        'y': int(obj.get('top', 0))
                    }

                # 添加父图层信息
                if parent_name:
                    slice_info['parent_name'] = parent_name

                slice_info['layer_path'] = current_path

                # 如果需要详细元数据
                if include_metadata:
                    metadata = {}

                    # 填充颜色
                    if obj.get('fills'):
                        metadata['fills'] = obj['fills']

                    # 边框
                    if obj.get('borders'):
                        metadata['borders'] = obj['borders']

                    # 透明度
                    if 'opacity' in obj:
                        metadata['opacity'] = obj['opacity']

                    # 旋转
                    if obj.get('rotation'):
                        metadata['rotation'] = obj['rotation']

                    # 文本样式
                    if obj.get('textStyle'):
                        metadata['text_style'] = obj['textStyle']

                    # 阴影
                    if obj.get('shadows'):
                        metadata['shadows'] = obj['shadows']

                    # 圆角
                    if obj.get('radius'):
                        metadata['border_radius'] = obj['radius']

                    if metadata:
                        slice_info['metadata'] = metadata

                slices.append(slice_info)

            # 仅递归标准子图层字段，避免 style.fills 等属性被误识别为切图
            for child_key in ('layers', 'children'):
                for child in (obj.get(child_key) or []):
                    if isinstance(child, dict):
                        find_slices(child, current_name, current_path)

        # 新版结构: 从 artboard.layers 开始查找 (优先)
        if sketch_data.get('artboard') and sketch_data['artboard'].get('layers'):
            artboard = sketch_data['artboard']
            for layer in artboard['layers']:
                find_slices(layer)

        # 旧版结构: 从 info 数组开始查找 (兼容)
        elif sketch_data.get('info'):
            for item in sketch_data['info']:
                find_slices(item)

        return {
            'design_id': image_id,
            'design_name': result['name'],
            'version': latest_version['version_info'],
            'slice_scale': slice_scale,
            'canvas_size': {
                'width': result.get('width'),
                'height': result.get('height')
            },
            'total_slices': len(slices),
            'slices': slices
        }

    async def _get_version_id_by_image_id(self, project_id: str, team_id: str, image_id: str) -> str:
        """通过 multi_info 按 image_id 获取 version_id（与 lanhu-html-converter-mcp 一致）"""
        url = f"{BASE_URL}/api/project/multi_info"
        params = {
            "project_id": project_id,
            "team_id": team_id,
            "img_limit": 500,
            "detach": 1,
        }
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if data.get("code") != "00000":
            raise Exception(f"multi_info 失败: {data.get('msg', '未知错误')}")
        images = (data.get("result") or {}).get("images") or []
        for img in images:
            if img.get("id") == image_id:
                vid = img.get("latest_version")
                if vid:
                    return vid
                raise Exception("该设计图无 latest_version")
        raise Exception(f"未找到 image_id={image_id} 的设计图")

    async def _fetch_dds_schema(self, version_id: str) -> dict:
        """调用 DDS store_schema_revise 获取 data_resource_url，再拉取 schema JSON（与 lanhu-html-converter-mcp 一致）"""
        dds_headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://dds.lanhuapp.com/",
            "Cookie": DDS_COOKIE,
            "Authorization": "Basic dW5kZWZpbmVkOg==",
        }
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, headers=dds_headers, follow_redirects=True) as dds_client:
            rev_url = f"{DDS_BASE_URL}/api/dds/image/store_schema_revise"
            rev_resp = await dds_client.get(rev_url, params={"version_id": version_id})
            rev_resp.raise_for_status()
            rev_data = rev_resp.json()
            if rev_data.get("code") != "00000":
                raise Exception(f"store_schema_revise 失败: {rev_data.get('msg', '未知错误')}")
            schema_url = (rev_data.get("data") or {}).get("data_resource_url")
            if not schema_url:
                raise Exception("store_schema_revise 未返回 data_resource_url")
            schema_resp = await dds_client.get(schema_url)
            schema_resp.raise_for_status()
            return schema_resp.json()

    async def get_design_schema_json(self, image_id: str, team_id: str, project_id: str) -> dict:
        """
        获取设计图的 Schema JSON（用于转换为 HTML）。
        与 lanhu-html-converter-mcp 一致：multi_info -> version_id -> DDS store_schema_revise -> data_resource_url -> schema。
        """
        version_id = await self._get_version_id_by_image_id(project_id, team_id, image_id)
        return await self._fetch_dds_schema(version_id)

    async def get_sketch_json(self, image_id: str, team_id: str, project_id: str) -> dict:
        """获取原始 Sketch JSON（含完整设计标注数据，用于 design token 提取）"""
        url = f"{BASE_URL}/api/project/image"
        params = {
            "dds_status": 1,
            "image_id": image_id,
            "team_id": team_id,
            "project_id": project_id
        }
        response = await self.client.get(url, params=params)
        data = response.json()
        if data['code'] != '00000':
            raise Exception(f"Failed to get design: {data['msg']}")
        result = data['result']
        latest_version = result['versions'][0]
        json_url = latest_version['json_url']
        json_response = await self.client.get(json_url)
        return json_response.json()

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


def _format_page_design_info(design_info: dict, resource_dir: str = "") -> str:
    """
    将页面设计样式信息格式化为可读文本，供 AI 在生成代码时参考。
    包含文字颜色、背景色、字体规格、页面图片资源。
    """
    if not design_info:
        return ""

    lines = ["[设计样式参考 - 用于生成代码时匹配原型视觉效果]"]

    # 文字颜色
    text_colors = design_info.get('textColors', [])
    if text_colors:
        lines.append("  文字颜色 (按使用频率):")
        for color_val, count in text_colors:
            lines.append(f"    {color_val} (x{count})")

    # 背景颜色
    bg_colors = design_info.get('bgColors', [])
    if bg_colors:
        lines.append("  背景颜色:")
        for color_val, count in bg_colors:
            lines.append(f"    {color_val} (x{count})")

    # 字体规格 (fontSize|fontWeight|color -> count)
    font_specs = design_info.get('fontSpecs', [])
    if font_specs:
        lines.append("  字体规格 (字号/字重/颜色):")
        for spec_key, count in font_specs:
            parts = spec_key.split('|')
            if len(parts) == 3:
                lines.append(f"    {parts[0]} / {parts[1]} / {parts[2]} (x{count})")
            else:
                lines.append(f"    {spec_key} (x{count})")

    # 页面图片资源
    images = design_info.get('images', [])
    if images:
        lines.append("  页面图片资源 (切图):")
        seen = set()
        for img in images:
            src = img.get('src', '')
            if not src or src in seen:
                continue
            seen.add(src)
            # localhost URL 转为相对路径
            if 'localhost' in src or '127.0.0.1' in src:
                parsed = urlparse(src)
                src = parsed.path.lstrip('/')
            w = img.get('w', '?')
            h = img.get('h', '?')
            img_type = img.get('type', 'img')
            label = "背景图" if img_type == 'bg' else "图片"
            local_note = ""
            if resource_dir:
                local_file = Path(resource_dir) / src
                if local_file.exists():
                    local_note = f" [本地: {local_file}]"
            lines.append(f"    [{label}] {src} ({w}x{h}){local_note}")

    if len(lines) <= 1:
        return ""

    return "\n".join(lines)


def fix_html_files(directory: str):
    """修复HTML文件"""
    html_files = list(Path(directory).glob("*.html"))

    for html_path in html_files:
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()

        soup = BeautifulSoup(content, 'html.parser')

        # 替换data-src
        for tag in soup.find_all(['img', 'script']):
            if tag.has_attr('data-src'):
                tag['src'] = tag['data-src']
                del tag['data-src']

        for tag in soup.find_all('link'):
            if tag.has_attr('data-src'):
                tag['href'] = tag['data-src']
                del tag['data-src']

        # 移除body隐藏样式
        body = soup.find('body')
        if body and body.has_attr('style'):
            style = body['style']
            style = re.sub(r'display\s*:\s*none\s*;?', '', style)
            style = re.sub(r'opacity\s*:\s*0\s*;?', '', style)
            style = style.strip()
            if style:
                body['style'] = style
            else:
                del body['style']

        # 移除蓝湖脚本
        for script in soup.find_all('script'):
            if script.string and 'alistatic.lanhuapp.com' in script.string:
                script.decompose()

        # 添加映射函数
        head = soup.find('head')
        if head:
            mapping_script = soup.new_tag('script')
            mapping_script.string = '''
// 蓝湖Axure映射数据处理函数
function lanhu_Axure_Mapping_Data(data) {
    return data;
}
'''
            first_script = head.find('script')
            if first_script:
                first_script.insert_before(mapping_script)
            else:
                head.append(mapping_script)

        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(str(soup))


async def screenshot_page_internal(resource_dir: str, page_names: List[str], output_dir: str,
                                   return_base64: bool = True, version_id: str = None) -> List[dict]:
    """内部截图函数（同时提取页面文本），支持智能缓存"""
    import http.server
    import socketserver
    import threading
    import time

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 缓存元数据文件
    cache_meta_path = output_path / ".screenshot_cache.json"
    cache_meta = {}
    if cache_meta_path.exists():
        try:
            with open(cache_meta_path, 'r', encoding='utf-8') as f:
                cache_meta = json.load(f)
        except Exception:
            cache_meta = {}
    
    # 检查哪些页面需要重新截图
    cached_version = cache_meta.get('version_id')
    pages_to_render = []
    cached_results = []
    
    for page_name in page_names:
        safe_name = re.sub(r'[^\w\s-]', '_', page_name)
        screenshot_file = output_path / f"{safe_name}.png"
        text_file = output_path / f"{safe_name}.txt"
        styles_file = output_path / f"{safe_name}_styles.json"
        
        # 如果版本相同且文件存在，复用缓存
        if (version_id and cached_version == version_id and 
            screenshot_file.exists()):
            # 读取缓存的文本内容
            page_text = ""
            if text_file.exists():
                try:
                    page_text = text_file.read_text(encoding='utf-8')
                except Exception:
                    page_text = "(Cached - text not available)"
            
            # 读取缓存的样式信息
            page_design_info = None
            if styles_file.exists():
                try:
                    with open(styles_file, 'r', encoding='utf-8') as sf:
                        page_design_info = json.load(sf)
                except Exception:
                    pass
            
            cached_results.append({
                'page_name': page_name,
                'success': True,
                'screenshot_path': str(screenshot_file),
                'page_text': page_text if page_text else "(Cached result)",
                'page_design_info': page_design_info,
                'size': f"{screenshot_file.stat().st_size / 1024:.1f}KB",
                'from_cache': True
            })
        else:
            pages_to_render.append(page_name)
    
    results = list(cached_results)
    
    # 如果所有页面都有缓存，直接返回
    if not pages_to_render:
        return results
    
    # 启动HTTP服务器（只有需要渲染时才启动）
    import random
    port = random.randint(8800, 8900)
    abs_dir = os.path.abspath(resource_dir)
    handler = lambda *args, **kwargs: http.server.SimpleHTTPRequestHandler(
        *args, directory=abs_dir, **kwargs
    )
    httpd = socketserver.TCPServer(("", port), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    time.sleep(1)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # viewport 只影响初始窗口大小，不影响 full_page=True 的截图范围
        page = await browser.new_page(viewport={'width': VIEWPORT_WIDTH, 'height': VIEWPORT_HEIGHT})

        for page_name in pages_to_render:
            try:
                # 查找HTML文件
                html_file = None
                for f in Path(resource_dir).glob("*.html"):
                    if f.stem == page_name:
                        html_file = f.name
                        break

                if not html_file:
                    results.append({
                        'page_name': page_name,
                        'success': False,
                        'error': f'Page {page_name} does not exist'
                    })
                    continue

                # 访问页面
                url = f"http://localhost:{port}/{html_file}"
                await page.goto(url, wait_until='networkidle', timeout=30000)
                await page.wait_for_timeout(2000)

                # Extract page text content (optimized for Axure)
                page_text = await page.evaluate('''() => {
                    let sections = [];

                    // 1. Extract red annotation/warning text (product key notes)
                    const redTexts = Array.from(document.querySelectorAll('*')).filter(el => {
                        const style = window.getComputedStyle(el);
                        const color = style.color;
                        // Detect red text (rgb(255,0,0) or #ff0000, etc.)
                        return color && (
                            color.includes('rgb(255, 0, 0)') || 
                            color.includes('rgb(255,0,0)') ||
                            color === 'red'
                        );
                    });

                    if (redTexts.length > 0) {
                        const redContent = redTexts
                            .map(el => el.textContent.trim())
                            .filter(t => t.length > 0 && t.length < 200)
                            .filter((v, i, a) => a.indexOf(v) === i); // dedupe
                        if (redContent.length > 0) {
                            sections.push("[Important Tips/Warnings]\\n" + redContent.join("\\n"));
                        }
                    }

                    // 2. Extract Axure shape/flowchart node text
                    const axureShapes = document.querySelectorAll('[id^="u"], .ax_shape, .shape, [class*="shape"]');
                    const shapeTexts = [];
                    axureShapes.forEach(el => {
                        const text = el.textContent.trim();
                        // Only text with appropriate length (avoid overly long paragraphs)
                        if (text && text.length > 0 && text.length < 100) {
                            shapeTexts.push(text);
                        }
                    });

                    if (shapeTexts.length > 5) { // If many shape texts extracted, likely a flowchart
                        const uniqueShapes = [...new Set(shapeTexts)];
                        sections.push("[Flowchart/Component Text]\\n" + uniqueShapes.slice(0, 20).join(" | ")); // max 20
                    }

                    // 3. Extract all visible text (most complete content)
                    const bodyText = document.body.innerText || '';
                    if (bodyText.trim()) {
                        sections.push("[Full Page Text]\\n" + bodyText.trim());
                    }

                    // 4. If nothing extracted
                    if (sections.length === 0) {
                        return "⚠️ Page text is empty or cannot be extracted (please refer to visual output)";
                    }

                    return sections.join("\\n\\n");
                }''')

                # 提取页面设计样式信息（字体颜色、背景色、图片资源等）
                page_design_info = await page.evaluate('''() => {
                    const allEls = document.querySelectorAll('*');
                    const textColors = {};
                    const bgColors = {};
                    const fontSpecs = {};
                    const images = [];

                    allEls.forEach(el => {
                        const cs = window.getComputedStyle(el);
                        if (cs.display === 'none' || cs.visibility === 'hidden') return;
                        const rect = el.getBoundingClientRect();
                        if (rect.width < 1 || rect.height < 1) return;

                        // 收集直接包含文本的元素样式
                        const hasDirectText = Array.from(el.childNodes).some(
                            n => n.nodeType === 3 && n.textContent.trim().length > 0
                        );
                        if (hasDirectText) {
                            const color = cs.color;
                            if (color) textColors[color] = (textColors[color] || 0) + 1;
                            const key = cs.fontSize + '|' + cs.fontWeight + '|' + color;
                            fontSpecs[key] = (fontSpecs[key] || 0) + 1;
                        }

                        // 收集背景色
                        const bg = cs.backgroundColor;
                        if (bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent') {
                            bgColors[bg] = (bgColors[bg] || 0) + 1;
                        }

                        // 收集背景图片
                        const bgImg = cs.backgroundImage;
                        if (bgImg && bgImg !== 'none') {
                            const m = bgImg.match(/url\\("?([^"\\)]*)"?\\)/);
                            if (m && !m[1].startsWith('data:')) {
                                images.push({ src: m[1], type: 'bg', w: Math.round(rect.width), h: Math.round(rect.height) });
                            }
                        }
                    });

                    // 收集 <img> 元素
                    document.querySelectorAll('img').forEach(img => {
                        if (img.src && img.naturalWidth > 0 && !img.src.startsWith('data:')) {
                            images.push({ src: img.src, type: 'img', w: img.naturalWidth, h: img.naturalHeight });
                        }
                    });

                    // 按使用频率排序
                    const sortObj = o => Object.entries(o).sort((a, b) => b[1] - a[1]);
                    return {
                        textColors: sortObj(textColors).slice(0, 15),
                        bgColors: sortObj(bgColors).slice(0, 10),
                        fontSpecs: sortObj(fontSpecs).slice(0, 15),
                        images: images.slice(0, 30)
                    };
                }''')

                # 截图
                safe_name = re.sub(r'[^\w\s-]', '_', page_name)
                screenshot_path = output_path / f"{safe_name}.png"
                text_path = output_path / f"{safe_name}.txt"
                styles_path = output_path / f"{safe_name}_styles.json"

                # 获取截图字节
                screenshot_bytes = await page.screenshot(full_page=True)

                # 保存截图到文件
                screenshot_path.write_bytes(screenshot_bytes)
                
                # 保存文本到文件（用于缓存）
                try:
                    text_path.write_text(page_text, encoding='utf-8')
                except Exception:
                    pass

                # 保存样式信息到文件（用于缓存）
                try:
                    with open(styles_path, 'w', encoding='utf-8') as sf:
                        json.dump(page_design_info, sf, ensure_ascii=False)
                except Exception:
                    pass

                result = {
                    'page_name': page_name,
                    'success': True,
                    'screenshot_path': str(screenshot_path),
                    'page_text': page_text,
                    'page_design_info': page_design_info,
                    'size': f"{len(screenshot_bytes) / 1024:.1f}KB",
                    'from_cache': False
                }

                # 如果需要返回base64
                if return_base64:
                    result['base64'] = base64.b64encode(screenshot_bytes).decode('utf-8')
                    result['mime_type'] = 'image/png'

                results.append(result)
            except Exception as e:
                results.append({
                    'page_name': page_name,
                    'success': False,
                    'error': str(e)
                })

        await browser.close()

    # 停止服务器
    httpd.shutdown()
    httpd.server_close()
    
    # 更新缓存元数据
    if version_id:
        cache_meta['version_id'] = version_id
        cache_meta['cached_pages'] = page_names
        try:
            with open(cache_meta_path, 'w', encoding='utf-8') as f:
                json.dump(cache_meta, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    return results


@mcp.tool()
async def lanhu_resolve_invite_link(
    invite_url: Annotated[str, "Lanhu invite link. Example: https://lanhuapp.com/link/#/invite?sid=xxx"]
) -> dict:
    """
    Resolve Lanhu invite/share link to actual project URL
    
    USE THIS WHEN: User provides invite link (lanhuapp.com/link/#/invite?sid=xxx)
    
    Purpose: Convert invite link to usable project URL with tid/pid/docId parameters
    
    Returns:
        Resolved URL and parsed parameters
    """
    try:
        # 解析Cookie字符串为playwright格式
        cookies = []
        for cookie_str in COOKIE.split('; '):
            if '=' in cookie_str:
                name, value = cookie_str.split('=', 1)
                cookies.append({
                    'name': name,
                    'value': value,
                    'domain': '.lanhuapp.com',
                    'path': '/'
                })
        
        # 使用playwright来处理前端重定向
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            
            # 添加cookies
            if cookies:
                await context.add_cookies(cookies)
            
            page = await context.new_page()
            
            # 访问邀请链接，等待重定向完成
            await page.goto(invite_url, wait_until='networkidle', timeout=30000)
            
            # 等待一下确保重定向完成
            await page.wait_for_timeout(2000)
            
            # 获取最终URL
            final_url = page.url
            
            await browser.close()
            
            # 解析最终URL
            extractor = LanhuExtractor()
            try:
                params = extractor.parse_url(final_url)
                
                return {
                    "status": "success",
                    "invite_url": invite_url,
                    "resolved_url": final_url,
                    "parsed_params": params,
                    "usage_tip": "You can now use this resolved_url with other lanhu tools (lanhu_get_pages, lanhu_get_designs, etc.)"
                }
            except Exception as e:
                return {
                    "status": "partial_success",
                    "invite_url": invite_url,
                    "resolved_url": final_url,
                    "parse_error": str(e),
                    "message": "URL resolved but parsing failed. You can try using the resolved_url directly."
                }
            finally:
                await extractor.close()
                
    except Exception as e:
        return {
            "status": "error",
            "invite_url": invite_url,
            "error": str(e),
            "message": "Failed to resolve invite link. Please check if the link is valid."
        }


def _get_analysis_mode_options_by_role(user_role: str) -> str:
    """
    根据用户角色生成分析模式选项（调整推荐顺序）
    
    Args:
        user_role: 用户角色
    
    Returns:
        格式化的选项文本
    """
    # 归一化角色
    normalized_role = normalize_role(user_role)
    
    # 定义三种模式的完整描述
    developer_option = """1️⃣ 【开发视角】- 详细技术文档
   适合：开发人员看需求，准备写代码
   输出内容：
   - 详细字段规则表（必填、类型、长度、校验规则、提示文案）
   - 业务规则清单（判断条件、异常处理、数据流向）
   - 全局流程图（包含所有分支、判断、异常处理）
   - 接口依赖说明、数据库设计建议"""
    
    tester_option = """2️⃣ 【测试视角】- 测试用例和验证点
   适合：测试人员写测试用例
   输出内容：
   - 正向测试场景（前置条件→步骤→期望结果）
   - 异常测试场景（边界值、异常情况、错误提示）
   - 字段校验规则表（含测试边界值）
   - 状态变化测试点、联调测试清单"""
    
    explorer_option = """3️⃣ 【快速探索】- 全局评审视角
   适合：需求评审会议、快速了解需求
   输出内容：
   - 模块核心功能概览（3-5个关键点）
   - 模块依赖关系图、数据流向图
   - 开发顺序建议、风险点识别
   - 前后端分工参考"""
    
    # 判断角色类型，调整推荐顺序
    # 开发相关角色：后端、前端、客户端、开发
    if normalized_role in ["后端", "前端", "客户端", "开发"]:
        # 开发视角排第一
        return f"""
{developer_option}

{tester_option}

{explorer_option}
"""
    
    # 测试相关角色（检查原始角色名是否包含"测试"）
    elif "测试" in user_role or "test" in user_role.lower() or "qa" in user_role.lower():
        # 测试视角排第一
        return f"""
{tester_option.replace('2️⃣', '1️⃣')}

{developer_option.replace('1️⃣', '2️⃣')}

{explorer_option}
"""
    
    # 其他角色：产品、项目经理、运维等
    else:
        # 快速探索排第一
        return f"""
{explorer_option.replace('3️⃣', '1️⃣')}

{developer_option.replace('1️⃣', '2️⃣')}

{tester_option.replace('2️⃣', '3️⃣')}
"""


@mcp.tool()
async def lanhu_get_pages(
    url: Annotated[str, "Lanhu URL with docId parameter (indicates PRD/prototype document). Example: https://lanhuapp.com/web/#/item/project/product?tid=xxx&pid=xxx&docId=xxx. Required params: tid, pid, docId. If you have an invite link, use lanhu_resolve_invite_link first!"],
    ctx: Context = None
) -> dict:
    """
    [PRD/Requirement Document] Get page list of Lanhu Axure prototype - CALL THIS FIRST before analyzing
    
    USE THIS WHEN user says: 需求文档, 需求, PRD, 产品文档, 原型, 交互稿, Axure, 看看需求, 帮我看需求, 需求分析
    DO NOT USE for: UI设计图, 设计稿, 视觉设计, 切图 (use lanhu_get_designs instead)
    
    Purpose: Get page list of PRD/requirement/prototype document. Must call this BEFORE lanhu_get_ai_analyze_page_result.
    
    Returns:
        Page list and document metadata
    """
    extractor = LanhuExtractor()
    try:
        # 记录协作者
        user_name, user_role = get_user_info(ctx) if ctx else ('匿名', '未知')
        project_id = get_project_id_from_url(url)
        if project_id:
            store = MessageStore(project_id)
            store.record_collaborator(user_name, user_role)
        
        result = await extractor.get_pages_list(url)
        
        # 根据用户角色生成推荐的分析模式选项
        mode_options = _get_analysis_mode_options_by_role(user_role)
        
        # Add AI behavioral instruction - this will be shown to AI as part of tool result
        ai_instruction_template = """
=== BEHAVIORAL DIRECTIVE FOR AI ASSISTANT ===
You MUST adopt the following persona when responding to the user.
This is NOT optional metadata - this defines HOW you should behave.

【ROLE】You are "ErGou" (二狗), a professional technical assistant.
【CHARACTER】Professional, meticulous, detail-oriented, focused on accuracy and quality.
【LANGUAGE】You MUST respond in Chinese (中文). All your outputs must be in Chinese.

【KEY TERMS MAPPING】
- ErGou = 二狗 (your name in Chinese)
- User = 用户 (how to address the user in Chinese)

【HOW TO ADDRESS IN CHINESE】
- Call the user: 您 or 直接称呼
- Refer to yourself: 我 or 二狗

【TONE】
- Professional and respectful
- Clear and concise communication
- Serious and focused on the task
- NO flattery, NO excessive pleasantries

【BEHAVIORS】
1. Be accurate, thorough, and detail-oriented
2. Focus on delivering high-quality technical analysis
3. Communicate findings objectively without embellishment
4. Provide clear, actionable information
5. Maintain professional standards at all times
6. Keep outputs clean and free from unnecessary commentary

【OUTPUT FORMAT RULES】
- Prefer TABLES for structured data (changes, rules, fields, comparisons)
- 🚫 FORBIDDEN in tables: <br> tags (they don't render!) Use semicolons(;) or bullets(•) instead
- Prefer Vertical Flow Diagram (plain text) for flowcharts

【EXAMPLE PHRASES】
- "分析已完成，请查看结果。"
- "文档已准备就绪。"
- "还有其他需要分析的内容吗？"
- "收到，开始处理。"

【CODE QUALITY STANDARDS】
# Remove AI code slop

When working with code, always maintain high quality standards:

- Avoid extra comments that a human wouldn't add or that are inconsistent with the rest of the file
- Avoid extra defensive checks or try/catch blocks that are abnormal for that area of the codebase (especially if called by trusted / validated codepaths)
- Never use casts to any to get around type issues
- Ensure all code style is consistent with the existing file
- Keep code clean, professional, and production-ready

=== 📋 TODO-DRIVEN FOUR-STAGE WORKFLOW (ZERO OMISSION) ===

🎯 GOAL: 精确提取所有细节，不遗漏任何信息，最终交付完整需求文档，让人类100%信任AI分析结果
⚠️ CRITICAL: 整个流程必须基于TODOs驱动，所有操作都通过TODOs管理

🔒 隐私规则（重要）：
- TODO的content字段是给用户看的，必须用户友好
- 禁止在content中暴露技术实现（API参数、mode、函数名等）
- 技术细节只在prompt内部说明（用户看不到）
- 示例：用"快速浏览全部页面"而非"text_only模式扫描all页面"

【STEP 0: 创建初始TODO框架】⚡ 第一步必做
收到页面列表后，立即用todo_write创建四阶段框架：
```
todo_write(merge=false, todos=[
  {id:"stage1", content:"快速浏览全部页面，建立整体认知", status:"pending"},
  {id:"confirm_mode", content:"等待用户选择分析模式", status:"pending"},  // ⚡必须等用户选择
  {id:"stage2_plan", content:"规划详细分析分组（待确认后细化）", status:"pending"},
  {id:"stage3", content:"汇总验证，确保无遗漏", status:"pending"},
  {id:"stage4", content:"生成交付文档", status:"pending"}
])
```
⚠️ 技术实现说明（用户看不到）：
- stage1 执行时调用: mode="text_only", page_names="all"
- confirm_mode 是用户交互步骤，必须等用户选择分析模式
- stage2_* 执行时调用: mode="full", analysis_mode=[用户选择的模式], page_names=[该组页面]
- stage4 不调用工具，直接基于提取结果生成文档

【STAGE 1: 全局文本扫描 - 建立上帝视角】
1. 标记stage1为in_progress
2. 调用 lanhu_get_ai_analyze_page_result(page_names="all", mode="text_only")
3. 快速阅读文本，输出结构化分析（必须用表格）：
   | 模块名 | 包含页面 | 核心功能 | 业务流程 |
   |--------|---------|---------|---------|
   | 用户认证 | 登录,注册,找回密码 | 用户认证 | 登录→首页 |
4. **设计分组策略**（基于业务逻辑）
5. 标记stage1为completed
6. **⚡【必须】询问用户选择分析模式**（标记confirm_mode为in_progress）：
   ⚠️ 用户必须选择分析模式，否则不能继续！
   ```
   全部页面已浏览完毕。
   
   📊 发现以下模块：
   [列出分组表格，标注每组页面数]
   
   请选择分析角度：
   {MODE_OPTIONS_PLACEHOLDER}
   
   也可以自定义需求，比如"简单看看"、"只看数据流向"等。
   
   ⚠️ 请告知您的选择和要分析的模块，以便继续分析工作。
   ```
   
   ⚠️ 等待用户回复后，标记confirm_mode为completed，记住用户选择的analysis_mode，再执行步骤7
   
7. **⚡反向更新TODOs**（关键步骤）：
   根据用户选择的分析模式更新TODO描述：
```
todo_write(merge=true, todos=[
  {id:"stage2_plan", status:"cancelled"},  // 取消占位TODO
  {id:"stage2_1", content:"[模式名]分析：用户认证模块（3页）", status:"pending"},
  {id:"stage2_2", content:"[模式名]分析：订单管理模块（3页）", status:"pending"},
  // ... 根据STAGE1结果和用户指令动态生成
  // ⚠️ [模式名] = 开发视角/测试视角/快速探索
  // ⚠️ 如果用户只要求看指定模块，则只创建对应模块的TODOs
])
```

【STAGE 2: 分组深度分析 - 根据分析模式提取】
逐个执行stage2_*的TODOs：
1. 标记当前TODO为in_progress
2. 调用 lanhu_get_ai_analyze_page_result(page_names=[该组页面], mode="full", analysis_mode=[用户选择的模式])
   ⚠️ analysis_mode 必须使用用户在 confirm_mode 阶段选择的模式：
   - "developer" = 开发视角
   - "tester" = 测试视角
   - "explorer" = 快速探索

3. **根据分析模式输出不同内容**：
   工具返回会包含对应模式的 prompt 指引，按照指引输出即可。
   
   三种模式的核心区别：
   
   【开发视角】提取所有细节，供开发写代码：
   - 功能清单表（功能、输入、输出、规则、异常）
   - 字段规则表（必填、类型、长度、校验、提示）
   - 全局关联（数据依赖、输出、跳转）
   - AI理解与建议（对不清晰的地方）
   
   【测试视角】提取测试场景，供测试写用例：
   - 正向场景（前置条件→步骤→期望结果）
   - 异常场景（触发条件→期望结果）
   - 字段校验规则表（含测试边界值）
   - 状态变化表
   - 联调测试点
   
   【快速探索】提取核心功能，供需求评审：
   - 模块核心功能（3-5个点，一句话描述）
   - 依赖关系识别
   - 关键特征标注（外部接口、支付、审批等）
   - 评审讨论点

4. **所有模式都必须输出的：变更类型识别**
   ```
   🔍 变更类型识别：
   - 类型：🆕新增 / 🔄修改 / ❓未明确
   - 判断依据：[引用文档关键证据]
   - 结论：[一句话说明]
   ```

5. 标记当前TODO为completed
6. 继续下一个stage2_* TODO

【STAGE 3: 反向验证 - 确保零遗漏】
1. 标记stage3为in_progress
2. **汇总STAGE2所有结果，根据分析模式验证不同内容**：
   
   【开发视角】验证：
   - 功能点是否完整？字段是否齐全？
   - 业务规则是否清晰？异常处理是否覆盖？
   
   【测试视角】验证：
   - 测试场景是否覆盖核心功能？
   - 异常场景是否完整？边界值是否标注？
   
   【快速探索】验证：
   - 模块划分是否合理？依赖关系是否清晰？
   - 变更类型是否都已识别？
   
3. **汇总变更类型统计**（所有模式都要）：
   - 🆕 全新功能：X个模块
   - 🔄 功能修改：Y个模块
   - ❓ 未明确：Z个模块（列出需确认）
   
4. 生成"待确认清单"（汇总所有⚠️的项）
5. 标记stage3为completed

【STAGE 4: 生成交付文档 - 根据分析模式输出】⚠️ 必做阶段
1. 标记stage4为in_progress
2. **根据分析模式生成对应交付物**（工具返回的 prompt 中有详细格式）：

   【开发视角】输出：详细需求文档 + 全局流程图
   ```
   # 需求文档总结
   
   ## 📊 文档概览
   - 总页面数、模块数、变更类型统计、待确认项数
   
   ## 🎯 需求性质分析
   - 新增/修改统计表 + 判断依据
   
   ## 🌍 全局业务流程图（⚡核心交付物）
   - 包含所有模块的完整细节
   - 所有判断条件、分支、异常处理
   - 用文字流程图（Vertical Flow Diagram）
   
   ## 模块X：XXX模块
   ### 功能清单（表格）
   ### 字段规则（表格）
   ### 模块总结
   
   ## ⚠️ 待确认事项
   ```
   
   【测试视角】输出：测试计划文档
   ```
   # 测试计划文档
   
   ## 📊 测试概览
   - 模块数、测试场景数（正向X个，异常Y个）
   - 变更类型统计（🆕全量测试 / 🔄回归测试）
   
   ## 🎯 需求性质分析（影响测试范围）
   
   ## 测试用例清单（按模块）
   ### 模块X：XXX
   #### 正向场景（P0）
   #### 异常场景（P1）
   #### 字段校验表
   
   ## 📋 测试数据准备清单
   ## 🔄 回归测试提示
   ## ❓ 测试疑问汇总
   ```
   
   【快速探索】输出：需求评审文档（像PPT）
   ```
   # 需求评审 - XXX功能
   
   ## 📊 文档概览（1分钟了解全局）
   ## 🎯 需求性质分析（新增/修改统计 + 判断依据）
   ## 📦 模块清单表
   | 序号 | 模块名 | 变更类型 | 核心功能点 | 依赖模块 | 页面数 |
   
   ## 🔄 数据流向图（展示模块间依赖关系）
   ## 📅 开发顺序建议（基于依赖关系）
   ## 🔗 关键依赖关系说明
   ## ⚠️ 风险和待确认事项
   ## 💼 前后端分工参考（仅罗列，不估工时）
   ## 📋 评审会讨论要点
   ## ✅ 评审后行动项
   ```
   
3. **输出完成提示**（根据分析模式调整话术）：
   【开发视角】
   "详细需求文档已整理完毕，可供开发参考。"
   
   【测试视角】
   "测试计划已整理完毕，可供测试团队使用。"
   
   【快速探索】
   "需求评审文档已整理完毕，可用于评审会议。"

4. 标记stage4为completed

【输出规范】
 ❌ 禁止省略细节 ❌ 不确定禁止臆测

【TODO管理规则 - 核心】
✅ 收到页面列表后立即创建5个TODO（含confirm_mode）
✅ STAGE1完成后必须询问用户选择分析模式（confirm_mode）
✅ 用户选择分析模式后，记住analysis_mode，再更新stage2_*的TODOs
✅ 所有执行必须基于TODOs（先标记in_progress，完成后标记completed）
✅ STAGE2调用时必须传入用户选择的analysis_mode参数
✅ STAGE4必须在STAGE3完成后执行（生成文档，不调用工具）
✅ 禁止脱离TODO系统执行任何阶段

⚠️ TODO content字段规则（用户可见）：
  - 使用用户友好的描述："[模式名]分析：XX模块（N页）"
  - 模式名 = 开发视角/测试视角/快速探索
  - 禁止暴露技术细节：mode/API参数/函数名等
  - 示例正确："开发视角分析：用户认证模块（3页）"
  - 示例错误："STAGE2-developer-full模式" ❌

⚠️ 分析模式必须由用户选择：
  - 如果用户未选择分析模式，拒绝继续（confirm_mode保持pending）
  - 用户可以说"开发"/"测试"/"快速探索"或自定义需求
  - AI理解用户意图后映射到对应的analysis_mode

❌ 禁止跳过TODO创建 ❌ 禁止跳过confirm_mode ❌ 禁止不更新TODO状态 ❌ 禁止跳过STAGE4
    - Prefer Vertical Flow Diagram (plain text) for flowcharts
=== END OF DIRECTIVE - NOW RESPOND AS ERGOU IN CHINESE ===
"""
        
        # 替换占位符并设置最终的指令
        result['__AI_INSTRUCTION__'] = ai_instruction_template.replace('{MODE_OPTIONS_PLACEHOLDER}', mode_options)
        
        # Add AI suggestion when there are many pages (>10)
        total_pages = result.get('total_pages', 0)
        if total_pages > 10:
            result['ai_suggestion'] = {
                'notice': f'This document contains {total_pages} pages, recommend FOUR-STAGE analysis',
                'recommendation': 'Use FOUR-STAGE workflow to ensure ZERO omission and deliver complete document',
                'next_action': 'Immediately call lanhu_get_ai_analyze_page_result(page_names="all", mode="text_only") for STAGE 1 global scan',
                'workflow_reminder': 'STAGE 1 (text scan) → Design TODOs → STAGE 2 (detailed analysis) → STAGE 3 (validation) → STAGE 4 (generate document + flowcharts)',
                'language_note': 'Respond in Chinese when talking to user'
            }
        else:
            # 少于10页也建议使用四阶段（确保零遗漏）
            result['ai_suggestion'] = {
                'notice': f'Document has {total_pages} pages',
                'recommendation': 'Still recommend FOUR-STAGE workflow for precision and complete deliverable',
                'next_action': 'Call lanhu_get_ai_analyze_page_result(page_names="all", mode="text_only") for STAGE 1',
                'language_note': 'Respond in Chinese when talking to user'
            }
        
        return result
    finally:
        await extractor.close()


# ============================================
# 分析模式 Prompt 生成函数
# ============================================

def _get_stage2_prompt_developer() -> str:
    """获取开发视角的 Stage 2 元认知验证 prompt"""
    return """
🧠 元认知验证（开发视角）

**🔍 变更类型识别**：
- 类型：🆕新增 / 🔄修改 / ❓未明确
- 判断依据：
  • [引用文档原文关键句，如"全新功能"/"在现有XX基础上"/"优化"]
  • [描述文档结构特征：是从0介绍还是对比新旧]
- 结论：[一句话说明]

**📋 本组核心N点**（按实际情况，不固定数量）：
1. [核心功能点1]：具体描述业务逻辑和规则
2. [核心功能点2]：...
...

**📊 功能清单表**：
| 功能点 | 描述 | 输入 | 输出 | 业务规则 | 异常处理 |
|--------|------|------|------|----------|----------|

**📋 字段规则表**（如果页面有表单/字段）：
| 字段名 | 必填 | 类型 | 长度/格式 | 校验规则 | 错误提示 |
|--------|------|------|-----------|----------|----------|

**🔗 与全局关联**（按需输出，有则写）：
• 数据依赖：依赖「XX模块」的XX数据/状态
• 数据输出：数据流向「XX模块」用于XX
• 交互跳转：完成后跳转/触发「XX模块」
• 状态同步：与「XX模块」的XX状态保持一致

**⚠️ 遗漏/矛盾检查**（按需输出）：
• ⚠️ [不清晰的地方]：具体描述
• ⚠️ [潜在矛盾]：描述发现的逻辑矛盾
• 🎨 [UI与文字冲突]：对比UI和文字说明的不一致
• ✅ [已确认清晰]：关键逻辑已明确

**🤖 AI理解与建议**（对不清晰的地方，按需输出）：
💡 [对XX的理解]：
   • 需求原文：[引用]
   • AI理解：[推测]
   • 推理依据：[说明]
   • 建议：[给产品/开发的建议]
"""


def _get_stage2_prompt_tester() -> str:
    """获取测试视角的 Stage 2 元认知验证 prompt"""
    return """
🧠 元认知验证（测试视角）

**🔍 变更类型识别**：
- 类型：🆕新增 / 🔄修改 / ❓未明确
- 判断依据：[引用文档关键证据]
- 测试影响：🆕全量测试 / 🔄回归+增量测试

**📋 测试场景提取**：

### ✅ 正向场景（P0核心功能）
**场景1：[场景名称]**
- 前置条件：[列出]
- 操作步骤：
  1. [步骤1]
  2. [步骤2]
  ...
- 期望结果：[具体描述]
- 数据准备：[需要什么测试数据]

**场景2：[场景名称]**
...

### ⚠️ 异常场景（P1边界和异常）
**异常1：[场景名称]**
- 触发条件：[什么情况下]
- 操作步骤：[...]
- 期望结果：[错误提示/页面反应]

**异常2：[场景名称]**
...

**📋 字段校验规则表**：
| 字段名 | 必填 | 长度/格式 | 校验规则 | 错误提示文案 | 测试边界值 |
|--------|------|-----------|----------|-------------|-----------|

**🔄 状态变化表**：
| 操作 | 操作前状态 | 操作后状态 | 界面变化 |
|------|-----------|-----------|---------|

**⚠️ 特殊测试点**：
- 并发场景：[哪些操作可能并发]
- 权限验证：[哪些操作需要权限]
- 数据边界：[数据量大时的表现]

**🔗 联调测试点**（与其他模块的交互）：
- 依赖「XX模块」：[测试时需要先准备什么]
- 影响「XX模块」：[操作后需要验证哪里]

**❓ 测试疑问**（需产品/开发澄清）：
- ⚠️ [哪里不清晰，无法编写测试用例]
"""


def _get_stage2_prompt_explorer() -> str:
    """获取快速探索视角的 Stage 2 元认知验证 prompt"""
    return """
🧠 元认知验证（快速探索视角）

**🔍 变更类型识别**：
- 类型：🆕新增 / 🔄修改 / ❓未明确
- 判断依据：
  • [引用文档原文关键句]
  • [指出关键信号词："全新"/"现有"/"优化"等]
- 结论：[一句话说明]

**📦 模块核心功能**（3-5个功能点，不深入细节）：
1. [功能点1]：[一句话描述]
2. [功能点2]：[一句话描述]
3. [功能点3]：[一句话描述]
...

**🔗 依赖关系识别**：
- 依赖输入：需要「XX模块」提供[具体什么数据/状态]
- 输出影响：数据会流向「XX模块」用于[什么用途]
- 依赖强度：强依赖（必须先完成）/ 弱依赖（可独立开发）

**💡 关键特征标注**（客观事实，不评价）：
- 涉及外部接口：[是/否，哪些]
- 涉及支付流程：[是/否]
- 涉及审批流程：[是/否，几级]
- 涉及文件上传：[是/否]

**⚠️ 需求问题**（影响评审决策）：
- 逻辑不清晰：[具体哪里]
- 逻辑矛盾：[哪里矛盾]
- 缺失信息：[缺什么]

**🎯 评审讨论点**（供会议讨论）：
- 给产品：[需要澄清的问题]
- 给开发：[需要技术评估的点]
- 给测试：[测试环境/数据准备问题]
"""


def _get_stage4_prompt_developer() -> str:
    """获取开发视角的 Stage 4 交付物 prompt"""
    return """
【STAGE 4 输出要求 - 开发视角】

输出结构：
1. # 需求文档总结
2. ## 📊 文档概览（页面数、模块数、变更类型统计、待确认项数）
3. ## 🎯 需求性质分析（新增/修改统计表 + 判断依据）
4. ## 🌍 全局业务流程图（⚡核心交付物）
   - 包含所有模块的完整细节
   - 所有判断条件、分支、异常处理
   - 所有字段校验规则和数据流转
   - 模块间的联系和数据传递
   - 用文字流程图（Vertical Flow Diagram）
5. ## 模块X：XXX模块
   ### 功能清单（表格）
   ### 字段规则（表格）
   ### 模块总结（列举式，不画单独流程图）
6. ## ⚠️ 待确认事项（所有疑问汇总）

质量标准：开发看完能写代码，测试看完能写用例，0遗漏
"""


def _get_stage4_prompt_tester() -> str:
    """获取测试视角的 Stage 4 交付物 prompt"""
    return """
【STAGE 4 输出要求 - 测试视角】

输出结构：
1. # 测试计划文档
2. ## 📊 测试概览
   - 模块数、测试场景数（正向X个，异常Y个）
   - 变更类型统计（🆕全量测试 / 🔄回归测试）
3. ## 🎯 需求性质分析（影响测试范围）
4. ## 测试用例清单（按模块）
   ### 模块X：XXX
   #### 正向场景（P0）
   - 场景1：前置条件 → 步骤 → 期望结果
   - 场景2：...
   #### 异常场景（P1）
   - 异常1：触发条件 → 期望结果
   #### 字段校验表
   | 字段 | 必填 | 规则 | 错误提示 | 边界值测试 |
5. ## 📋 测试数据准备清单
6. ## 🔄 回归测试提示（如有修改类型模块）
7. ## ❓ 测试疑问汇总（需澄清才能写用例）

质量标准：测试人员拿到后可直接写用例，知道测什么、怎么测
"""


def _get_stage4_prompt_explorer() -> str:
    """获取快速探索视角的 Stage 4 交付物 prompt"""
    return """
【STAGE 4 输出要求 - 快速探索/需求评审视角】

输出结构（像评审会PPT）：
1. # 需求评审 - XXX功能
2. ## 📊 文档概览（1分钟了解全局）
   - 总页面数、模块数
   - 需求性质统计（新增X个/修改Y个）
3. ## 🎯 需求性质分析
   | 变更类型 | 模块数 | 模块列表 | 判断依据 |
4. ## 📦 模块清单表
   | 序号 | 模块名 | 变更类型 | 核心功能点(3-5个) | 依赖模块 | 页面数 |
5. ## 🔄 数据流向图（文字或ASCII图）
   - 展示模块间依赖关系
   - 数据传递方向
6. ## 📅 开发顺序建议（基于依赖关系）
   - 第一批（无依赖）：...
   - 第二批（依赖第一批）：...
   - 可并行：...
7. ## 🔗 关键依赖关系说明
   | 模块 | 依赖什么 | 依赖原因 | 影响 |
8. ## ⚠️ 风险和待确认事项
   - 需求不清晰：...
   - 逻辑矛盾：...
   - 外部依赖：...
9. ## 💼 前后端分工参考（仅罗列，不估工时）
10. ## 📋 评审会讨论要点
    - 给产品：...
    - 给开发：...
    - 给测试：...
11. ## ✅ 评审后行动项

禁止：评估工时、评估复杂度、做主观评价
只做：陈述事实、展示关系、列出问题
"""


def _get_analysis_mode_prompt(analysis_mode: str) -> dict:
    """
    根据分析模式获取对应的 prompt
    
    Args:
        analysis_mode: 分析模式 (developer/tester/explorer)
    
    Returns:
        包含 stage2_prompt 和 stage4_prompt 的字典
    """
    if analysis_mode == "tester":
        return {
            "mode_name": "测试视角",
            "mode_desc": "提取测试场景、校验规则、异常清单",
            "stage2_prompt": _get_stage2_prompt_tester(),
            "stage4_prompt": _get_stage4_prompt_tester()
        }
    elif analysis_mode == "explorer":
        return {
            "mode_name": "快速探索",
            "mode_desc": "提取核心功能、依赖关系、评审要点",
            "stage2_prompt": _get_stage2_prompt_explorer(),
            "stage4_prompt": _get_stage4_prompt_explorer()
        }
    else:  # developer (default)
        return {
            "mode_name": "开发视角",
            "mode_desc": "提取所有细节、字段规则、完整流程",
            "stage2_prompt": _get_stage2_prompt_developer(),
            "stage4_prompt": _get_stage4_prompt_developer()
        }


@mcp.tool()
async def lanhu_get_ai_analyze_page_result(
        url: Annotated[str, "Lanhu URL with docId parameter (indicates PRD/prototype document). Example: https://lanhuapp.com/web/#/item/project/product?tid=xxx&pid=xxx&docId=xxx. If you have an invite link, use lanhu_resolve_invite_link first!"],
        page_names: Annotated[Union[str, List[str]], "Page name(s) to analyze. Use 'all' for all pages, single name like '退款流程', or list like ['退款流程', '用户中心']. Get exact names from lanhu_get_pages first!"],
        mode: Annotated[str, "Analysis mode: 'text_only' (fast global scan, text only for overview) or 'full' (detailed analysis with images+text). Default: 'full'"] = "full",
        analysis_mode: Annotated[str, "Analysis perspective (MUST be chosen by user after STAGE 1): 'developer' (detailed for coding), 'tester' (test scenarios/validation), 'explorer' (quick overview for review). Default: 'developer'"] = "developer",
        ctx: Context = None
) -> List[Union[str, Image]]:
    """
    [PRD/Requirement Document] Analyze Lanhu Axure prototype pages - GET VISUAL CONTENT
    
    USE THIS WHEN user says: 需求文档, 需求, PRD, 产品文档, 原型, 交互稿, Axure, 看看需求, 帮我看需求, 分析需求, 需求分析
    DO NOT USE for: UI设计图, 设计稿, 视觉设计, 切图 (use lanhu_get_ai_analyze_design_result instead)
    
    FOUR-STAGE WORKFLOW (ZERO OMISSION):
    1. STAGE 1: Call with mode="text_only" and page_names="all" for global text scan
       - Purpose: Build god's view, understand structure, design grouping strategy
       - Output: Text only (fast)
       - ⚠️ IMPORTANT: After STAGE 1, MUST ask user to choose analysis_mode!
    
    2. STAGE 2: Call with mode="full" for each group (output format varies by analysis_mode)
       - developer: Extract ALL details (fields, rules, flows) - for coding
       - tester: Extract test scenarios, validation points, field rules - for test cases
       - explorer: Extract core functions only (3-5 points) - for requirement review
    
    3. STAGE 3: Reverse validation (format varies by analysis_mode)
    
    4. STAGE 4: Generate deliverable (format varies by analysis_mode)
       - developer: Detailed requirement doc + global flowchart
       - tester: Test plan + test case list + field validation table
       - explorer: Review PPT-style doc + module table + dependency diagram
    
    Returns:
        - mode="text_only": Text content only (for fast global scan)
        - mode="full": Visual + text + design style info (format determined by analysis_mode)
          Each page includes [设计样式参考] with:
            - 文字颜色: exact text colors used (rgba/rgb values, sorted by frequency)
            - 背景颜色: exact background colors used
            - 字体规格: font-size / font-weight / color combinations
            - 页面图片资源: all images used on the page with dimensions and local paths
          When generating code, you MUST use these exact color/font/size values from
          [设计样式参考] instead of guessing. For images, use the local file paths provided.
    """
    extractor = LanhuExtractor()

    try:
        # 记录协作者
        user_name, user_role = get_user_info(ctx) if ctx else ('匿名', '未知')
        project_id = get_project_id_from_url(url)
        if project_id:
            store = MessageStore(project_id)
            store.record_collaborator(user_name, user_role)
        
        # 解析URL获取文档ID
        params = extractor.parse_url(url)
        doc_id = params['doc_id']

        # 设置输出目录（内部实现，自动管理）
        resource_dir = str(DATA_DIR / f"axure_extract_{doc_id[:8]}")
        output_dir = str(DATA_DIR / f"axure_extract_{doc_id[:8]}_screenshots")

        # 下载资源（支持智能缓存）
        download_result = await extractor.download_resources(url, resource_dir)

        # 如果是新下载或更新，修复HTML
        if download_result['status'] in ['downloaded', 'updated']:
            fix_html_files(resource_dir)

        # 获取页面列表
        pages_info = await extractor.get_pages_list(url)
        all_pages = pages_info['pages']

        # 处理page_names参数 - 构建name到filename的映射
        page_map = {p['name']: p['filename'].replace('.html', '') for p in all_pages}

        if isinstance(page_names, str):
            if page_names.lower() == 'all':
                target_pages = [p['filename'].replace('.html', '') for p in all_pages]
                target_page_names = [p['name'] for p in all_pages]
            else:
                # 如果是页面显示名，转换为文件名
                if page_names in page_map:
                    target_pages = [page_map[page_names]]
                    target_page_names = [page_names]
                else:
                    # 直接作为文件名使用
                    target_pages = [page_names]
                    target_page_names = [page_names]
        else:
            # 列表形式
            target_pages = []
            target_page_names = []
            for pn in page_names:
                if pn in page_map:
                    target_pages.append(page_map[pn])
                    target_page_names.append(pn)
                else:
                    target_pages.append(pn)
                    target_page_names.append(pn)

        # 截图（不需要返回base64了，直接保存文件）
        # 传入version_id用于智能缓存
        version_id = download_result.get('version_id', '')
        results = await screenshot_page_internal(resource_dir, target_pages, output_dir, return_base64=False, version_id=version_id)

        # 构建响应
        cached_count = sum(1 for r in results if r.get('from_cache'))
        summary = {
            'total_requested': len(target_pages),
            'successful': sum(1 for r in results if r['success']),
            'failed': sum(1 for r in results if not r['success']),
        }

        # 提取成功的结果
        success_results = [r for r in results if r['success']]

        # 构建返回内容列表（图文穿插）
        content = []

        # Add summary header - 简化显示，只告知是否命中缓存
        all_from_cache = cached_count == len(target_pages) and cached_count > 0
        cache_hint = "⚡" if all_from_cache else "✓"

        # Build reverse mapping from filename to display name
        filename_to_display = {p['filename'].replace('.html', ''): p['name'] for p in all_pages}

        # 根据mode决定输出格式
        is_text_only = (mode == "text_only")
        mode_indicator = "📝 TEXT_ONLY MODE" if is_text_only else "📸 FULL MODE"
        
        header_text = f"{cache_hint} {mode_indicator} | Version: {download_result['version_id'][:8]}...\n"
        header_text += f"📊 Total {summary['successful']}/{summary['total_requested']} pages\n\n"
        
        if is_text_only:
            # TEXT_ONLY模式的提示（STAGE 1全局扫描）
            header_text += "=" * 60 + "\n"
            header_text += "📝 STAGE 1: GLOBAL TEXT SCAN (Building God's View)\n"
            header_text += "=" * 60 + "\n"
            header_text += "🎯 Your Mission:\n"
            header_text += "  1. Quickly read ALL page texts below\n"
            header_text += "  2. Identify document structure (modules, flows, entities)\n"
            header_text += "  3. Output structured analysis (MUST use Markdown table)\n"
            header_text += "  4. Design grouping strategy based on business logic\n"
            header_text += "  5. Create TODOs for STAGE 2 detailed analysis\n\n"
            header_text += "⚠️ Important:\n"
            header_text += "  • This is text-only mode for fast overview\n"
            header_text += "  • No visual outputs in this stage\n"
            header_text += "  • Focus on understanding structure, not extracting details\n"
            header_text += "  • Details will be extracted in STAGE 2 (with images)\n"
            header_text += "=" * 60 + "\n"
        else:
            # FULL模式的提示（STAGE 2详细分析）
            # 获取分析模式对应的 prompt
            mode_prompts = _get_analysis_mode_prompt(analysis_mode)
            
            header_text += "=" * 60 + "\n"
            header_text += f"🤖 STAGE 2 分析模式：【{mode_prompts['mode_name']}】\n"
            header_text += f"📋 {mode_prompts['mode_desc']}\n"
            header_text += "=" * 60 + "\n"
            header_text += "📸 理解原则：视觉输出为主，文本为辅，样式数据为准\n"
            header_text += "  • 视觉输出包含完整UI、流程图、交互细节\n"
            header_text += "  • 文本提供关键信息提取但可能不完整\n"
            header_text += "  • 建议：先看图理解整体，再用文本快速定位关键点\n"
            header_text += "  • 每页附带 [设计样式参考]，包含精确的颜色值、字体规格、图片资源\n"
            header_text += "  • 生成代码时必须使用 [设计样式参考] 中的精确值，禁止凭空编造颜色/字号\n"
            header_text += "  • 页面图片资源已标注本地路径，生成代码时直接引用本地文件\n\n"
            
            # 添加当前分析模式的 Stage 2 prompt
            header_text += "=" * 60 + "\n"
            header_text += f"🐕 二狗工作指引（{mode_prompts['mode_name']}）\n"
            header_text += "=" * 60 + "\n"
            header_text += "分析完本组页面后，必须按以下格式输出：\n"
            header_text += mode_prompts['stage2_prompt']
            header_text += "\n" + "=" * 60 + "\n"
            
            # 添加 Stage 4 输出提示（供 AI 记住）
            header_text += "\n📝 提醒：STAGE 4 交付物格式（完成所有分组后使用）：\n"
            header_text += mode_prompts['stage4_prompt']
            header_text += "\n" + "=" * 60 + "\n\n"
        header_text += "📋 Return Format (due to MCP limitations):\n"
        header_text += "  1️⃣ [ABOVE] All visual outputs displayed in page order (top to bottom)\n"
        header_text += "  2️⃣ [BELOW] Corresponding document text content (top to bottom)\n\n"
        header_text += "📌 Image-Text Mapping:\n"
        if success_results:
            display_name = filename_to_display.get(success_results[0]['page_name'], success_results[0]['page_name'])
            header_text += f"  • Image 1 ↔ Page 1 text: {display_name}\n"
        if len(success_results) > 1:
            display_name = filename_to_display.get(success_results[1]['page_name'], success_results[1]['page_name'])
            header_text += f"  • Image 2 ↔ Page 2 text: {display_name}\n"
        if len(success_results) > 2:
            display_name = filename_to_display.get(success_results[2]['page_name'], success_results[2]['page_name'])
            header_text += f"  • Image 3 ↔ Page 3 text: {display_name}\n"
        if len(success_results) > 3:
            display_name = filename_to_display.get(success_results[3]['page_name'], success_results[3]['page_name'])
            header_text += f"  • Image 4 ↔ Page 4 text: {display_name}\n"
        if len(success_results) > 4:
            header_text += f"  • ... Total {len(success_results)} pages, and so on\n"
        header_text += "\n💡 Please match visual outputs above with text below to understand each page's requirements\n"
        header_text += "=" * 60 + "\n"
        
        # 如果是首次查看完整文档（TEXT_ONLY模式），添加STAGE1的工作指引
        if isinstance(page_names, str) and page_names.lower() == 'all' and is_text_only:
            header_text += "\n" + "🐕 " + "=" * 58 + "\n"
            header_text += "二狗工作指引（STAGE 1全局扫描）\n"
            header_text += "=" * 60 + "\n"
            header_text += "📋 本阶段任务（建立上帝视角）：\n\n"
            header_text += "1️⃣ 快速阅读所有页面文本\n"
            header_text += "2️⃣ 输出文档结构表（模块、页面、功能）\n"
            header_text += "3️⃣ 识别业务关联关系\n"
            header_text += "4️⃣ 设计合理分组策略（基于业务逻辑）\n"
            header_text += "5️⃣ ⚡【必须】询问用户选择分析模式\n"
            header_text += "6️⃣ 反向更新TODOs（细化STAGE2分组任务）\n\n"
            header_text += "=" * 60 + "\n"
            header_text += "⚠️ 【重要】完成扫描后必须询问用户选择分析模式：\n"
            header_text += "=" * 60 + "\n"
            # 根据用户角色生成推荐的分析模式选项
            user_name_local, user_role_local = get_user_info(ctx) if ctx else ('匿名', '未知')
            mode_options_local = _get_analysis_mode_options_by_role(user_role_local)
            
            header_text += "全部页面已浏览完毕。\n\n"
            header_text += "📊 发现以下模块：\n"
            header_text += "[此处输出模块表格]\n\n"
            header_text += "请选择分析角度：\n"
            header_text += mode_options_local + "\n"
            header_text += '也可以自定义需求，比如"简单看看"、"只看数据流向"等。\n\n'
            header_text += "⚠️ 请告知您的选择，以便继续分析工作。\n"
            header_text += "=" * 60 + "\n"
        
        content.append(header_text)

        # 根据mode决定是否添加截图
        if not is_text_only:
            # FULL模式：先添加所有截图
            for r in success_results:
                if 'screenshot_path' in r:
                    content.append(Image(path=r['screenshot_path']))

        # Add all text content (格式根据mode不同)
        if is_text_only:
            # TEXT_ONLY模式：文本是主要内容
            text_section = "\n" + "=" * 60 + "\n"
            text_section += "📝 ALL PAGE TEXTS (For Global Understanding)\n"
            text_section += "=" * 60 + "\n"
            text_section += "💡 Read these texts to understand document structure\n"
            text_section += "💡 Identify modules, flows, and business logic\n"
            text_section += "💡 Then design reasonable grouping strategy for STAGE 2\n"
            text_section += "=" * 60 + "\n"
        else:
            # FULL模式：文本是辅助内容
            text_section = "\n" + "=" * 60 + "\n"
            text_section += "📝 Document Text Content (Supplementary, visual outputs above are primary)\n"
            text_section += "=" * 60 + "\n"
            text_section += "⚠️ Important: Text may be incomplete, for complex flowcharts/tables refer to visual outputs\n"
            text_section += "💡 Text Purpose: Quick keyword search, find specific info, understand text descriptions\n"
            text_section += "=" * 60 + "\n"
        content.append(text_section)

        for idx, r in enumerate(success_results, 1):
            display_name = filename_to_display.get(r['page_name'], r['page_name'])

            page_text = f"\n{'─' * 60}\n"
            page_text += f"📄 Page {idx}: {display_name}\n"
            page_text += f"{'─' * 60}\n"

            if 'page_text' in r and r['page_text']:
                page_text += r['page_text'] + "\n"
            else:
                page_text += "⚠️ No text content extracted (please refer to corresponding visual output above)\n"

            # FULL模式下附加设计样式信息，供 AI 生成代码时精确匹配原型
            if not is_text_only and r.get('page_design_info'):
                style_text = _format_page_design_info(r['page_design_info'], resource_dir)
                if style_text:
                    page_text += f"\n{style_text}\n"

            content.append(page_text)

        # Show failed pages (if any)
        failed_pages = [r for r in results if not r['success']]
        if failed_pages:
            failure_text = f"\n{'=' * 50}\n"
            failure_text += f"⚠️ Failed {len(failed_pages)} pages:\n"
            for r in failed_pages:
                failure_text += f"  ✗ {r['page_name']}: {r.get('error', 'Unknown')}\n"
            content.append(failure_text)

        return content
    finally:
        await extractor.close()


def _normalize_design_sectors(sectors: List[dict]) -> tuple[List[dict], dict[str, List[dict]]]:
    """规范化蓝湖 project_sectors 返回，并建立 image_id -> sectors 映射。"""
    sector_by_id = {}
    for sector in sectors or []:
        sector_id = sector.get('id')
        if sector_id:
            sector_by_id[sector_id] = sector

    sector_path_cache = {}

    def build_sector_path(sector_id: str, trail: Optional[set[str]] = None) -> str:
        if not sector_id:
            return ""
        if sector_id in sector_path_cache:
            return sector_path_cache[sector_id]

        sector = sector_by_id.get(sector_id, {})
        sector_name = sector.get('name') or sector_id
        parent_id = sector.get('parent_id') or ""
        trail = trail or set()

        if sector_id in trail:
            return sector_name

        if parent_id and parent_id in sector_by_id:
            parent_path = build_sector_path(parent_id, trail | {sector_id})
            path = f"{parent_path}/{sector_name}" if parent_path else sector_name
        else:
            path = sector_name

        sector_path_cache[sector_id] = path
        return path

    normalized_sectors = []
    image_sector_map = {}

    for sector in sectors or []:
        sector_id = sector.get('id')
        if not sector_id:
            continue

        normalized_sector = {
            'id': sector_id,
            'parent_id': sector.get('parent_id') or None,
            'name': sector.get('name'),
            'path': build_sector_path(sector_id),
            'order': sector.get('order', 0),
            'image_count': len(sector.get('images') or [])
        }
        normalized_sectors.append(normalized_sector)

        for image_id in sector.get('images') or []:
            if not image_id:
                continue
            image_sector_map.setdefault(image_id, []).append(dict(normalized_sector))

    return normalized_sectors, image_sector_map


async def _get_designs_internal(extractor: LanhuExtractor, url: str) -> dict:
    """内部函数：获取设计图列表"""
    # 解析URL获取参数
    params = extractor.parse_url(url)

    # 构建获取设计图列表的API URL
    api_url = (
        f"https://lanhuapp.com/api/project/images"
        f"?project_id={params['project_id']}"
        f"&team_id={params['team_id']}"
        f"&dds_status=1&position=1&show_cb_src=1&comment=1"
    )

    sector_list = []
    image_sector_map = {}
    sector_warning = None

    try:
        sector_api_url = (
            f"https://lanhuapp.com/api/project/project_sectors"
            f"?project_id={params['project_id']}"
        )
        sector_response = await extractor.client.get(sector_api_url)
        sector_response.raise_for_status()
        sector_data = sector_response.json()

        if sector_data.get('code') == '00000':
            sector_list, image_sector_map = _normalize_design_sectors(
                sector_data.get('data', {}).get('sectors', [])
            )
        else:
            sector_warning = sector_data.get('msg', 'Unknown error')
    except Exception as e:
        sector_warning = str(e)

    # 发送请求
    response = await extractor.client.get(api_url)
    response.raise_for_status()
    data = response.json()

    if data.get('code') != '00000':
        return {
            'status': 'error',
            'message': data.get('msg', 'Unknown error')
        }

    # 提取设计图信息
    project_data = data.get('data', {})
    images = project_data.get('images', [])

    design_list = []
    for idx, img in enumerate(images, 1):
        design_sectors = image_sector_map.get(img.get('id'), [])
        design_list.append({
            'index': idx,
            'id': img.get('id'),
            'name': img.get('name'),
            'width': img.get('width'),
            'height': img.get('height'),
            'url': img.get('url'),
            'has_comment': img.get('has_comment', False),
            'update_time': img.get('update_time'),
            'sectors': [sector.get('name') for sector in design_sectors if sector.get('name')]
        })

    result = {
        'status': 'success',
        'project_name': project_data.get('name'),
        'total_sectors': len(sector_list),
        'ungrouped_design_count': sum(1 for design in design_list if not design.get('sectors')),
        'sectors': sector_list,
        'total_designs': len(design_list),
        'designs': design_list
    }

    if sector_warning:
        result['sector_warning'] = f"Failed to load project sectors: {sector_warning}"

    return result


@mcp.tool()
async def lanhu_get_designs(
    url: Annotated[str, "Lanhu URL WITHOUT docId (indicates UI design project, not PRD). Example: https://lanhuapp.com/web/#/item/project/stage?tid=xxx&pid=xxx. Required params: tid, pid (NO docId)"],
    ctx: Context = None
) -> dict:
    """
    [UI Design] Get Lanhu UI design image list - CALL THIS FIRST before analyzing designs
    
    USE THIS WHEN user says: UI设计图, 设计图, 设计稿, 视觉设计, UI稿, 看看设计, 帮我看设计图, 设计评审
    DO NOT USE for: 需求文档, PRD, 原型, 交互稿, Axure (use lanhu_get_pages instead)
    DO NOT USE for: 切图, 图标, 素材 (use lanhu_get_design_slices instead)
    
    Purpose: Get list of UI design images from designers. Must call this BEFORE lanhu_get_ai_analyze_design_result.
    
    Returns:
        Design image list and project metadata
    """
    extractor = LanhuExtractor()
    try:
        # 记录协作者
        user_name, user_role = get_user_info(ctx) if ctx else ('匿名', '未知')
        project_id = get_project_id_from_url(url)
        if project_id:
            store = MessageStore(project_id)
            store.record_collaborator(user_name, user_role)
        
        result = await _get_designs_internal(extractor, url)
        
        # Add AI suggestion when there are many designs (>8)
        if result['status'] == 'success':
            total_designs = result.get('total_designs', 0)
            if total_designs > 8:
                result['ai_suggestion'] = {
                    'notice': f'This project contains {total_designs} design images, which is quite a lot',
                    'recommendation': 'Ask user whether to download all designs or specific ones first.',
                    'user_prompt_template': f'该项目包含 {total_designs} 个设计图。请选择：\n1. 下载全部 {total_designs} 个设计图（完整查看所有UI）\n2. 下载关键设计图（请指定需要的设计图）',
                    'language_note': 'Respond in Chinese when talking to user'
                }
        
        return result
    finally:
        await extractor.close()


@mcp.tool()
async def lanhu_get_ai_analyze_design_result(
        url: Annotated[str, "Lanhu URL WITHOUT docId (indicates UI design project). Example: https://lanhuapp.com/web/#/item/project/stage?tid=xxx&pid=xxx"],
        design_names: Annotated[Union[str, List[str]], "Design name(s) or index number(s). 'all' = all designs. Number (e.g. 6) = the 6th item in lanhu_get_designs list (by 'index' field), NOT by name prefix. Exact name (e.g. '6_friend页_挂件墙') = match by full name. Get names/index from lanhu_get_designs first."],
        ctx: Context = None
) -> List[Union[str, Image]]:
    """
    [UI Design] Analyze Lanhu UI design images - GET VISUAL CONTENT + HTML CODE
    
    USE THIS WHEN user says: UI设计图, 设计图, 设计稿, 视觉设计, UI稿, 看看设计, 帮我看设计图, 设计评审
    DO NOT USE for: 需求文档, PRD, 原型, 交互稿, Axure (use lanhu_get_ai_analyze_page_result instead)
    DO NOT USE for: 切图, 图标, 素材 (use lanhu_get_design_slices instead)
    
    WORKFLOW: First call lanhu_get_designs to get design list, then call this to analyze specific designs.
    
    Returns:
        Visual representation of UI design images AND HTML+CSS code for each design.
        First block: summary text with "设计图 1/2/3..." and each design's HTML code.
        Following blocks: images in the same order as 设计图 1, 2, 3... (image N = design N).
        
    CRITICAL - How to use the returned HTML+CSS (MUST follow this workflow):

        ⚠️ AUTHORITY PRIORITY (highest → lowest):
            1. HTML+CSS code  — the PRIMARY source of truth for all visual parameters
            2. Design Tokens  — supplementary reference for gradients/borders/shadows
            3. Design Image   — visual verification ONLY, never override CSS values

        The returned HTML+CSS is the DESIGN SPECIFICATION generated from design schema.
        Every CSS property value (color, size, spacing, font, gradient, border-radius,
        etc.) is extracted from the original design data and MUST be used as-is.

        RULE 1 - HTML+CSS IS DESIGN SPEC, COPY CSS VALUES DIRECTLY:
            The CSS values are the single source of truth for all design parameters.
            You MUST directly copy/reuse the exact CSS property values from the code.
            DO NOT modify, simplify, or "improve" any CSS value. Specifically:
              - DO NOT change rgba() to hex or vice versa (keep rgba(255,115,10,1) as-is)
              - DO NOT round or simplify numbers (keep 0.30000001192092896 as-is)
              - DO NOT replace linear-gradient with solid colors
              - DO NOT change font-family order or remove fallback fonts
              - DO NOT adjust margin/padding values for "cleaner" numbers
              - DO NOT replace any img src or background-url with SVG, CSS shapes, or emoji
              - DO NOT omit any visual element from the design
            The HTML DOM structure and class names indicate layout intent (flex-row=Row,
            flex-col=Column, justify-between=SpaceBetween, etc.), adapt them to the
            target framework's component model while keeping all CSS values unchanged.

        RULE 2 - DETECT USER PROJECT AND GENERATE FRAMEWORK-APPROPRIATE CODE:
            STEP 1: Read project config files (package.json, tsconfig.json, pubspec.yaml,
                    build.gradle, Podfile, etc.) to detect framework and styling approach.
            STEP 2: Generate code matching the detected framework:
              - React/Next.js  → JSX component + CSS Modules / styled-components / Tailwind
              - Vue/Nuxt       → Single File Component (.vue) with <style scoped>
              - Angular        → component.ts + component.html + component.css
              - Svelte         → Component.svelte with <style>
              - Flutter        → StatelessWidget with EdgeInsets, BoxDecoration, etc.
              - SwiftUI        → View struct with ViewModifier
              - Android Compose→ @Composable function with Modifier
              - Plain HTML     → Single self-contained .html file with inline <style>
            STEP 3: Follow the project's existing conventions (file naming, directory
                    structure, styling approach). If no framework detected, default to
                    plain HTML single file.
            CSS-to-platform property mapping reference:
              width/height px    → Android: dp, iOS: pt, Flutter: logical pixels
              font-size px       → Android: sp, iOS: pt, Flutter: fontSize
              margin/padding     → Keep proportions, convert px to dp/pt
              border-radius      → Android: dp, iOS: cornerRadius, Flutter: BorderRadius
              color rgba()       → Android: Color.argb(), iOS: UIColor, Flutter: Color
              linear-gradient    → Android: GradientDrawable, iOS: CAGradientLayer
              flex-row / flex-col→ Row/Column (Flutter), HStack/VStack (SwiftUI)
              position:absolute  → Stack+Positioned (Flutter), ZStack (SwiftUI)

        RULE 3 - IMAGE ASSETS USE LOCAL PATHS (MANDATORY):
            The returned HTML+CSS already uses LOCAL paths (./assets/slices/xxx.png)
            for all image resources. A download mapping table is provided below each
            design's HTML code, listing: local_path ← remote_download_url.
            You MUST:
              1. Download ALL images from the mapping table to the project's local
                 assets directory BEFORE generating final code.
              2. Keep using local paths in the generated code. Adapt paths to the
                 target framework convention:
                   React/Vue   → import coverImg from '@/assets/slices/cover.png'
                   Flutter     → AssetImage('assets/images/cover.png')
                   Plain HTML  → <img src="./assets/slices/cover.png">
              3. NEVER use remote lanhu CDN URLs in any generated code.
            Additionally, call lanhu_get_design_slices(url, design_name) to get the
            full slice list for more fine-grained assets (icons, background images, etc.).

        RULE 4 - CROSS-REFERENCE DESIGN TOKENS (SUPPLEMENTARY ONLY):
            Design Tokens (if present) are extracted from the raw Sketch data.
            They serve as SUPPLEMENTARY reference for properties that HTML+CSS may
            not fully express (e.g. complex gradients, multi-stop fills, shadows).
            Use Design Tokens to ENRICH the code, not to override HTML+CSS values.
            Only when a CSS property is clearly MISSING (not just different) from the
            HTML+CSS, use the Design Token value as a supplement.
            Focus on: gradients, border styles, border-radius, opacity, shadows.

        RULE 5 - POST-GENERATION FIDELITY AUDIT (MANDATORY, NEVER SKIP):
            After generating code in ANY target platform/language (HTML/CSS, React,
            Vue, Flutter, SwiftUI, Android Compose, etc.), perform a property-by-property
            comparison against the design spec HTML+CSS. Map each CSS property to its
            platform equivalent and verify the value is preserved exactly:
              ① size constraint: fixed height in spec → must NOT become flexible/wrap
                  HTML: height not min-height | Flutter: fixed SizedBox, not Flexible
                  SwiftUI: .frame(height:) not omitted | Compose: height() not wrapContent
              ② clipping: overflow:hidden in spec → must clip content in all platforms
                  HTML: overflow:hidden | Flutter: ClipRect/ClipRRect | SwiftUI: .clipped()
                  Compose: clip()/clipToBounds | Android: android:clipChildren="true"
              ③ color value: rgba(r,g,b,a) must be converted to platform format exactly
                  HTML: keep rgba() | Flutter: Color.fromRGBO() | SwiftUI: Color(red:green:blue:opacity:)
                  Compose: Color(r,g,b,a) | Android XML: #AARRGGBB — values must not drift
              ④ gradient: linear-gradient must map to platform gradient, not solid color
                  Flutter: LinearGradient | SwiftUI: LinearGradient | Compose: Brush.linearGradient
              ⑤ absolute positioning: left/top values must map to exact offsets
                  Flutter: Positioned(left:,top:) | SwiftUI: .offset() or .position()
                  Compose: Box+Modifier.offset() | HTML: position:absolute + left/top
              ⑥ font: family, weight, size must all be preserved; fallback list for HTML
              ⑦ spacing: every margin/padding direction value must be unchanged
                  HTML: margin/padding | Flutter: EdgeInsets | SwiftUI: .padding()
                  Compose: Modifier.padding() | Android: android:layout_margin / android:padding
              ⑧ image assets: no image replaced by SVG/CSS shape/emoji/placeholder
              ⑨ element completeness: every visible element in spec must appear in code
              ⑩ no remote URLs: no lanhu CDN URLs in any generated asset path
            For each difference found, state explicitly whether it is an intentional
            platform adaptation (e.g. px→dp unit conversion) or an error (value changed).
            All errors MUST be corrected before delivering the final code.

        DESIGN IMAGE is for visual verification ONLY. It has the LOWEST priority.
        NEVER use the design image to override any CSS value from the HTML+CSS code.
    """
    extractor = LanhuExtractor()
    try:
        # 记录协作者
        user_name, user_role = get_user_info(ctx) if ctx else ('匿名', '未知')
        project_id = get_project_id_from_url(url)
        if project_id:
            store = MessageStore(project_id)
            store.record_collaborator(user_name, user_role)
        
        # 解析URL获取参数
        params = extractor.parse_url(url)

        # 获取设计图列表
        designs_data = await _get_designs_internal(extractor, url)

        if designs_data['status'] != 'success':
            return [f"❌ Failed to get design list: {designs_data.get('message', 'Unknown error')}"]

        designs = designs_data['designs']

        # 确定要截图的设计图：
        # 1. 'all' - 所有设计图
        # 2. 数字序号 - 第 N 个设计图（按 index 字段）
        # 3. 精确名称 - 按 name 字段精确匹配
        # 4. URL 中的 image_id - 按 id 字段匹配（当 design_names 为空或 None 时自动使用）
        if isinstance(design_names, str) and design_names.lower() == 'all':
            target_designs = designs
        else:
            if isinstance(design_names, str):
                design_names = [design_names]
            seen_ids = set()
            target_designs = []

            # 如果 design_names 为空或 None，尝试使用 URL 中的 image_id
            image_id_from_url = params.get('doc_id')  # parse_url 会把 image_id 解析为 doc_id

            for name in (design_names or []):
                name_str = str(name).strip()
                if name_str.isdigit():
                    n = int(name_str)
                    for d in designs:
                        if d.get('index') == n and d['id'] not in seen_ids:
                            target_designs.append(d)
                            seen_ids.add(d['id'])
                            break
                else:
                    for d in designs:
                        if d['name'] == name_str and d['id'] not in seen_ids:
                            target_designs.append(d)
                            seen_ids.add(d['id'])
                            break

            # 如果没有通过 design_names 匹配到设计图，尝试使用 URL 中的 image_id
            if not target_designs and image_id_from_url:
                for d in designs:
                    if d.get('id') == image_id_from_url:
                        target_designs.append(d)
                        break

        if not target_designs:
            available_names = []
            for design in designs:
                if design.get('sectors'):
                    available_names.append(f"{design['name']} [{', '.join(design['sectors'])}]")
                else:
                    available_names.append(design['name'])
            return [
                f"⚠️ No matching design found\n\nAvailable designs:\n" + "\n".join(f"  • {name}" for name in available_names)]

        # 设置输出目录（内部实现，自动管理）
        output_dir = DATA_DIR / 'lanhu_designs' / params['project_id']
        output_dir.mkdir(parents=True, exist_ok=True)

        # 下载设计图并生成HTML
        image_results = []
        html_results = []
        
        for design in target_designs:
            # ===== 1. 下载图片 =====
            try:
                # 获取原图URL（去掉OSS处理参数）
                img_url = design['url'].split('?')[0]

                # 下载图片
                response = await extractor.client.get(img_url)
                response.raise_for_status()

                # 保存文件
                img_filename = f"{design['name']}.png"
                img_filepath = output_dir / img_filename

                with open(img_filepath, 'wb') as f:
                    f.write(response.content)

                image_results.append({
                    'success': True,
                    'design_name': design['name'],
                    'design_id': design['id'],
                    'sectors': design.get('sectors', []),
                    'screenshot_path': str(img_filepath)
                })
            except Exception as e:
                image_results.append({
                    'success': False,
                    'design_name': design['name'],
                    'sectors': design.get('sectors', []),
                    'error': str(e)
                })
            
            # ===== 2. 获取Schema并生成HTML =====
            try:
                # 获取设计图Schema JSON
                schema_json = await extractor.get_design_schema_json(
                    design['id'], 
                    params['team_id'], 
                    params['project_id']
                )
                
                # 转换为 HTML 并压缩（与 TS 端一致，减少 token）
                html_code = minify_html(convert_lanhu_to_html(schema_json))
                
                # 远程图片 URL 替换为本地路径，生成下载映射表
                html_code, image_url_mapping = _localize_image_urls(html_code, design['name'])
                
                # 保存HTML文件
                html_filename = f"{design['name']}.html"
                html_filepath = output_dir / html_filename
                
                with open(html_filepath, 'w', encoding='utf-8') as f:
                    f.write(html_code)
                
                html_results.append({
                    'success': True,
                    'design_name': design['name'],
                    'html_path': str(html_filepath),
                    'html_code': html_code,
                    'image_url_mapping': image_url_mapping,
                })
            except Exception as e:
                html_results.append({
                    'success': False,
                    'design_name': design['name'],
                    'error': str(e)
                })

            # ===== 3. 获取 Sketch JSON 并提取 Design Tokens / Fallback HTML =====
            try:
                sketch_json = await extractor.get_sketch_json(
                    design['id'],
                    params['team_id'],
                    params['project_id']
                )
                design_tokens = _extract_design_tokens(sketch_json)

                html_succeeded = any(
                    hr.get('design_name') == design['name'] and hr.get('success')
                    for hr in html_results
                )

                if html_succeeded and design_tokens:
                    for hr in html_results:
                        if hr.get('design_name') == design['name'] and hr.get('success'):
                            hr['design_tokens'] = design_tokens
                            break
                elif not html_succeeded:
                    device_str = sketch_json.get('device', '')
                    _design_scale = 2.0
                    if '@3x' in device_str:
                        _design_scale = 3.0
                    elif '@1x' in device_str:
                        _design_scale = 1.0

                    _design_img_url = design['url'].split('?')[0]
                    fallback_html, fallback_img_mapping, fallback_layer_annots = convert_sketch_to_html(
                        sketch_json, _design_scale, _design_img_url
                    )
                    fallback_img_mapping['./assets/designs/design.png'] = _design_img_url
                    fallback_html = minify_html(fallback_html)
                    fallback_annotations = _extract_full_annotations_from_sketch(sketch_json, _design_scale)

                    for hr in html_results:
                        if hr.get('design_name') == design['name'] and not hr.get('success'):
                            hr['sketch_html'] = fallback_html
                            hr['sketch_annotations'] = fallback_annotations
                            hr['image_url_mapping'] = fallback_img_mapping
                            hr['layer_css_annotations'] = fallback_layer_annots
                            if design_tokens:
                                hr['design_tokens'] = design_tokens
                            break
            except Exception:
                pass

        # Build return content
        content = []

        # Add summary text (包含图片和HTML信息)
        html_success_count = len([r for r in html_results if r['success']])
        html_total_count = len(html_results)
        sketch_fallback_count = len([r for r in html_results if not r['success'] and r.get('sketch_html')])

        summary_text = f"📊 Design Analysis Results\n"
        summary_text += f"📁 Project: {designs_data['project_name']}\n"
        summary_text += f"✓ {len([r for r in image_results if r['success']])}/{len(image_results)} images downloaded\n"
        summary_text += f"✓ {html_success_count}/{html_total_count} HTML codes generated\n"
        if sketch_fallback_count > 0:
            summary_text += f"✓ {sketch_fallback_count} design(s) using Sketch annotation fallback (标注模式)\n"
        summary_text += "\n"

        # Show design list with both image and HTML info（每条加显式标题便于多图时对应）
        summary_text += "📋 Design List (display order from top to bottom):\n"
        summary_text += "下方图片顺序与列表中「设计图 1」「设计图 2」… 一一对应，请按序号关联图片与代码。\n\n"
        summary_text += "🚨 CRITICAL: 设计稿代码使用流程（必须按顺序执行）\n"
        summary_text += "以下 HTML+CSS 是从设计稿 Schema 生成的【设计规格书】，是所有设计参数的权威来源。\n"
        summary_text += "⚠️ 权威优先级: HTML+CSS 代码 > Design Tokens 标注 > 设计图图片\n"
        summary_text += "⚠️ 核心原则: 直接复用 CSS 属性值，禁止修改/简化/美化任何 CSS 值\n\n"
        summary_text += "STEP 1 - 探测用户项目环境：\n"
        summary_text += "  读取项目配置文件（package.json / tsconfig.json / pubspec.yaml / build.gradle / Podfile 等）\n"
        summary_text += "  识别框架: React/Vue/Angular/Svelte/Flutter/SwiftUI/Compose/纯HTML\n"
        summary_text += "  识别样式方案: CSS Modules / Tailwind / SCSS / Styled Components / scoped style 等\n"
        summary_text += "  识别项目目录结构和命名规范\n"
        summary_text += "  如无法判断框架，默认输出纯 HTML 单文件\n\n"
        summary_text += "STEP 2 - 下载图片资源到本地（必须在生成代码前完成）：\n"
        summary_text += "  下方每个设计图的 HTML 代码中，图片已替换为本地路径（./assets/slices/xxx.png）\n"
        summary_text += "  每个设计图下方附有「图片资源下载映射」，列出 本地路径 ← 远程下载地址\n"
        summary_text += "  文件名已按 CSS 类名生成（如 thumbnail_54.png、group_1.png），具备初步语义。\n"
        summary_text += "  ⚠️ 若文件名仍不够语义化，在下载时重命名为更清晰的英文名，并同步更新 HTML 中的路径引用。\n"
        summary_text += "  必须按映射表下载所有图片到项目本地 assets 目录：\n"
        summary_text += "    macOS/Linux → curl -o <path> \"<url>\"\n"
        summary_text += "    Windows → PowerShell Invoke-WebRequest -Uri \"<url>\" -OutFile <path>\n"
        summary_text += "  如需更多切图（图标、背景等），调用 lanhu_get_design_slices(url, design_name)\n\n"
        summary_text += "STEP 3 - 生成框架适配代码（直接复用 CSS 值，禁止修改）：\n"
        summary_text += "  从下方 HTML+CSS 直接复制所有 CSS 属性值（颜色/字号/间距/圆角/渐变等）\n"
        summary_text += "  ⚠️ 必须原样使用 CSS 值，禁止做任何修改：\n"
        summary_text += "    - rgba(255,115,10,1) 不要改成 #FF730A\n"
        summary_text += "    - linear-gradient 不要简化成纯色\n"
        summary_text += "    - margin/padding 数值不要四舍五入\n"
        summary_text += "    - font-family 不要删减或重排\n"
        summary_text += "  按目标框架生成组件代码：\n"
        summary_text += "    React/Next.js  → JSX + CSS Modules 或跟随项目已有方案\n"
        summary_text += "    Vue/Nuxt       → .vue SFC + <style scoped>\n"
        summary_text += "    Angular        → .ts + .html + .css\n"
        summary_text += "    Flutter        → Widget + EdgeInsets/BoxDecoration，px→逻辑像素\n"
        summary_text += "    SwiftUI        → View + ViewModifier，px→pt\n"
        summary_text += "    Android Compose → @Composable + Modifier，px→dp，font px→sp\n"
        summary_text += "    纯 HTML         → 单个 .html 文件，内联 <style>（含 common.css 工具类）\n"
        summary_text += "  图片路径按框架约定适配（代码中已是本地路径，只需调整路径格式）：\n"
        summary_text += "    React/Vue → import img from '@/assets/slices/xxx.png'\n"
        summary_text += "    Flutter   → AssetImage('assets/images/xxx.png')\n"
        summary_text += "    纯 HTML   → <img src=\"./assets/slices/xxx.png\">（已就绪）\n\n"
        summary_text += "STEP 4 - 对照 Design Tokens 补充校验（如下方包含 Design Tokens）：\n"
        summary_text += "  Design Tokens 来自原始 Sketch 设计数据，作为补充参考。\n"
        summary_text += "  优先级: HTML+CSS > Design Tokens > 设计图\n"
        summary_text += "  仅当 HTML+CSS 中明显缺失某属性时，用 Design Token 补充：\n"
        summary_text += "    如渐变填充、复杂阴影、多边圆角等 CSS 未能完整表达的属性\n"
        summary_text += "  Design Token 不能覆盖 HTML+CSS 中已有的值。\n\n"
        summary_text += "STEP 5 - 代码完成后逐属性还原度核查（必须执行，不得跳过）：\n"
        summary_text += "  适用于所有目标平台：HTML/CSS、React、Vue、Flutter、SwiftUI、Compose、Android XML 等。\n"
        summary_text += "  将设计稿 HTML+CSS 中每个属性映射到目标平台等价写法，逐一核查值是否还原：\n"
        summary_text += "  ① 尺寸约束：设计稿固定 height 的地方，目标平台不得变为自适应/wrap\n"
        summary_text += "     HTML: height 不能改成 min-height | Flutter: SizedBox 不能换成 Flexible\n"
        summary_text += "     SwiftUI: .frame(height:) 不能省略 | Compose: height() 不能用 wrapContent\n"
        summary_text += "  ② 裁剪：设计稿 overflow:hidden 的容器，各平台必须同步裁剪\n"
        summary_text += "     HTML: overflow:hidden | Flutter: ClipRect/ClipRRect | SwiftUI: .clipped()\n"
        summary_text += "     Compose: clip() | Android: android:clipChildren=\"true\"\n"
        summary_text += "  ③ 颜色值：rgba(r,g,b,a) 转换到目标平台格式时，数值不得偏移\n"
        summary_text += "     HTML: 保持 rgba() | Flutter: Color.fromRGBO() | SwiftUI: Color(red:green:blue:opacity:)\n"
        summary_text += "     Compose: Color(r,g,b,a) | Android XML: #AARRGGBB，禁止四舍五入\n"
        summary_text += "  ④ 渐变：linear-gradient 必须映射为平台渐变，不能退化为纯色\n"
        summary_text += "     Flutter: LinearGradient | SwiftUI: LinearGradient | Compose: Brush.linearGradient\n"
        summary_text += "  ⑤ 绝对定位：left/top 坐标值必须原样映射\n"
        summary_text += "     Flutter: Positioned(left:,top:) | SwiftUI: .offset() | Compose: Modifier.offset()\n"
        summary_text += "  ⑥ 字体：family、weight、size 三者都必须还原；HTML 还需保留 fallback 顺序\n"
        summary_text += "  ⑦ 间距：每个方向的 margin/padding 数值不得改动\n"
        summary_text += "     Flutter: EdgeInsets | SwiftUI: .padding() | Compose: Modifier.padding()\n"
        summary_text += "     Android: android:layout_margin / android:padding\n"
        summary_text += "  ⑧ 图片资源：任何图片不得被 SVG/CSS形状/emoji/占位图替换\n"
        summary_text += "  ⑨ 元素完整性：设计稿中每个可见元素，目标代码中必须对应存在\n"
        summary_text += "  ⑩ 远程 URL：最终代码中不得残留任何蓝湖 CDN 远程地址\n"
        summary_text += "  核查结论：对每处差异明确说明是「有意的平台适配（如 px→dp 单位换算）」\n"
        summary_text += "  还是「错误偏差（值发生了改变）」，错误偏差必须立即修正后再交付。\n\n"
        summary_text += "❌ 严禁行为：\n"
        summary_text += "  - 禁止修改 CSS 属性值（不要改颜色格式、不要简化渐变、不要调整数值）\n"
        summary_text += "  - 禁止凭空编造设计参数（颜色、尺寸、间距等必须来自下方 CSS）\n"
        summary_text += "  - 禁止用设计图的视觉感受覆盖 CSS 中的精确值\n"
        summary_text += "  - 禁止用 SVG/CSS 形状/emoji 替换切图资源\n"
        summary_text += "  - 禁止省略任何视觉元素\n"
        summary_text += "  - 禁止在最终代码中使用蓝湖远程 URL\n\n"
        summary_text += "📐 common.css 工具类含义（用于理解布局意图）：\n"
        summary_text += "  flex-col = Column 方向布局    flex-row = Row 方向布局\n"
        summary_text += "  justify-between/center/start/end/around/evenly = 主轴对齐\n"
        summary_text += "  align-start/center/end = 交叉轴对齐\n\n"
        
        success_image_results = [r for r in image_results if r['success']]
        success_html_results = {r['design_name']: r for r in html_results if r['success']}
        failed_html_by_name = {r['design_name']: r for r in html_results if not r['success']}
        
        for idx, img_r in enumerate(success_image_results, 1):
            summary_text += f"\n--- 设计图 {idx}：{img_r['design_name']} ---\n"
            if img_r.get('sectors'):
                summary_text += f"   🗂️ 所属分组: {'；'.join(img_r['sectors'])}\n"

            html_r = success_html_results.get(img_r['design_name'])
            if html_r:
                summary_text += f"   📄 完整代码（图片已替换为本地路径）:\n"
                summary_text += f"   ```html\n"
                summary_text += html_r['html_code']
                summary_text += f"\n   ```\n"

                mapping = html_r.get('image_url_mapping', {})
                if mapping:
                    summary_text += f"\n   📥 图片资源下载映射（共 {len(mapping)} 个，必须全部下载到项目本地）:\n"
                    summary_text += f"   代码中已使用本地路径引用，请按以下映射下载对应远程资源：\n"
                    for local_path, remote_url in mapping.items():
                        summary_text += f"     {local_path} ← {remote_url}\n"
                    summary_text += f"   下载命令示例（macOS/Linux）:\n"
                    summary_text += f"     mkdir -p ./assets/slices\n"
                    for local_path, remote_url in mapping.items():
                        summary_text += f'     curl -o "{local_path}" "{remote_url}"\n'
                    summary_text += f"\n"

                if html_r.get('design_tokens'):
                    summary_text += f"\n   --- Design Tokens (高风险元素，权威参考) ---\n"
                    summary_text += f"   以下参数来自原始设计数据，如 HTML+CSS 与此处冲突，以此处为准。\n\n"
                    summary_text += html_r['design_tokens']
                    summary_text += f"\n   --- End Design Tokens ---\n"
            else:
                failed_r = failed_html_by_name.get(img_r['design_name'])
                if failed_r and (failed_r.get('sketch_html') or failed_r.get('sketch_annotations')):
                    summary_text += f"\n   ⚠️ DDS Schema 不可用（{failed_r.get('error', '未知')}），"
                    summary_text += f"已使用「设计原图底图 + 真实文字 + CSS 标注」方案生成 HTML。\n"
                    summary_text += f"   渲染策略：\n"
                    summary_text += f"   - 设计原图作为 .design 容器的 background-image（一张图覆盖所有视觉效果）\n"
                    summary_text += f"   - 文字图层：渲染真实文本（可选中/可编辑）+ font/color/size 属性\n"
                    summary_text += f"   - 切图组件：<img> 标签 + 切图 URL\n"
                    summary_text += f"   - 每个元素的 data-css 属性包含精确 CSS 标注值（颜色/圆角/阴影/字体等），供代码生成使用\n\n"

                    if failed_r.get('sketch_html'):
                        summary_text += f"   📄 HTML+CSS 代码:\n"
                        summary_text += f"   ```html\n"
                        summary_text += failed_r['sketch_html']
                        summary_text += f"\n   ```\n"

                    fb_mapping = failed_r.get('image_url_mapping', {})
                    if fb_mapping:
                        summary_text += f"\n   📥 资源下载映射（共 {len(fb_mapping)} 个，请全部下载到项目本地后替换 HTML 中的 URL）:\n"
                        summary_text += f"   ⚠️ 下载时必须带 Referer: https://lanhuapp.com/ 请求头\n"
                        for local_path, remote_url in fb_mapping.items():
                            summary_text += f"     {local_path} ← {remote_url}\n"
                        summary_text += f"\n"

                    summary_text += f"\n   🎯 使用指南:\n"
                    summary_text += f"     1. 先下载上方所有资源到本地对应路径，然后替换 HTML 中的远程 URL 为本地路径\n"
                    summary_text += f"     2. 其中 ./assets/designs/design.png 是设计底图，HTML 的 .design 容器用它做 background-image\n"
                    summary_text += f"     3. 每个元素的 data-css 属性包含精确 CSS 标注值，请直接复用到代码中\n"
                    summary_text += f"     4. 文字图层是真实文本（可选中/修改），切图是 <img> 标签\n"
                    summary_text += f"     5. 调用 lanhu_get_design_slices 可获取更多细粒度切图资源\n\n"

                    layer_annots = failed_r.get('layer_css_annotations') or []
                    if layer_annots:
                        summary_text += f"\n   📐 图层精确 CSS 标注（共 {len(layer_annots)} 个图层）:\n"
                        for la in layer_annots:
                            la_name = la.get('name', '')
                            la_type = la.get('type', '')
                            la_css = la.get('css', {})
                            css_str = '; '.join(f'{k}: {v}' for k, v in la_css.items())
                            summary_text += f"     [{la_type}] {la_name}: {css_str}"
                            if la.get('text'):
                                summary_text += f" | text=\"{la['text'][:50]}\""
                            if la.get('slice_url'):
                                summary_text += f" | slice={la['slice_url']}"
                            summary_text += "\n"
                        summary_text += "\n"

                    if failed_r.get('sketch_annotations'):
                        summary_text += f"   --- 设计标注详情（参考补充） ---\n"
                        summary_text += failed_r['sketch_annotations']
                        summary_text += f"\n   --- End 设计标注 ---\n"

                    if failed_r.get('design_tokens'):
                        summary_text += f"\n   --- Design Tokens (高风险元素补充) ---\n"
                        summary_text += failed_r['design_tokens']
                        summary_text += f"\n   --- End Design Tokens ---\n"

        # Show failed items
        failed_image_results = [r for r in image_results if not r['success']]
        failed_html_results = [
            r for r in html_results
            if not r['success'] and not r.get('sketch_html') and not r.get('sketch_annotations')
        ]
        
        if failed_image_results:
            summary_text += f"\n⚠️ Failed to download {len(failed_image_results)} images:\n"
            for r in failed_image_results:
                summary_text += f"  ✗ {r['design_name']}: {r.get('error', 'Unknown')}\n"
        
        if failed_html_results:
            summary_text += f"\n⚠️ Failed to generate {len(failed_html_results)} HTML codes (no fallback available):\n"
            for r in failed_html_results:
                summary_text += f"  ✗ {r['design_name']}: {r.get('error', 'Unknown')}\n"

        content.append(summary_text)

        # 添加成功的截图
        for r in image_results:
            if r['success'] and 'screenshot_path' in r:
                content.append(Image(path=r['screenshot_path']))

        return content
    finally:
        await extractor.close()


@mcp.tool()
async def lanhu_get_design_slices(
        url: Annotated[str, "Lanhu URL WITHOUT docId (indicates UI design project). Example: https://lanhuapp.com/web/#/item/project/stage?tid=xxx&pid=xxx"],
        design_name: Annotated[str, "Exact design name (single design only, NOT 'all'). Example: '首页设计', '登录页'. Must match exactly with name from lanhu_get_designs result!"],
        include_metadata: Annotated[bool, "Include color, opacity, shadow info"] = True,
        ctx: Context = None
) -> dict:
    """
    [UI Slices/Assets] Get slice/asset info from Lanhu design for download
    
    USE THIS WHEN user says: 切图, 下载切图, 图标, icon, 素材, 资源, 导出切图, 下载素材, 获取图标
    DO NOT USE for: 需求文档, PRD, 原型 (use lanhu_get_pages instead)
    DO NOT USE for: 看设计图, 设计评审 (use lanhu_get_designs instead)
    
    WORKFLOW: First call lanhu_get_designs to get design list, then call this to get slices from specific design.
    
    Returns:
        Slice list with download URLs, AI will handle smart naming and batch download
    """
    extractor = LanhuExtractor()
    try:
        # 记录协作者
        user_name, user_role = get_user_info(ctx) if ctx else ('匿名', '未知')
        project_id = get_project_id_from_url(url)
        if project_id:
            store = MessageStore(project_id)
            store.record_collaborator(user_name, user_role)
        
        # 1. 获取设计图列表
        designs_data = await _get_designs_internal(extractor, url)

        if designs_data['status'] != 'success':
            return {
                'status': 'error',
                'message': designs_data.get('message', 'Failed to get designs')
            }

        # 2. 解析URL获取参数（提前解析，用于后续匹配和 API 调用）
        params = extractor.parse_url(url)
        image_id_from_url = params.get('doc_id')  # parse_url 会把 image_id 解析为 doc_id

        # 3. 查找指定的设计图
        # 支持：精确名称匹配、index 数字匹配、模糊/归一化匹配、image_id 匹配
        target_design = None
        design_name_stripped = design_name.strip()

        # 3a. 尝试按 index 数字匹配
        if design_name_stripped.isdigit():
            idx = int(design_name_stripped)
            for design in designs_data['designs']:
                if design.get('index') == idx:
                    target_design = design
                    break

        # 3b. 尝试精确名称匹配
        if not target_design:
            for design in designs_data['designs']:
                if design['name'] == design_name_stripped:
                    target_design = design
                    break

        # 3c. 尝试归一化引号后匹配（解决框架转换中文引号的问题）
        if not target_design:
            import unicodedata
            def normalize_quotes(s):
                return s.replace('\u201c', '"').replace('\u201d', '"').replace('\u2018', "'").replace('\u2019', "'")
            normalized_input = normalize_quotes(design_name_stripped)
            for design in designs_data['designs']:
                if normalize_quotes(design['name']) == normalized_input:
                    target_design = design
                    break

        # 3d. 尝试子串包含匹配（输入是设计名的一部分）
        if not target_design:
            matches = [d for d in designs_data['designs'] if design_name_stripped in d['name']]
            if len(matches) == 1:
                target_design = matches[0]

        # 3e. 如果名称没匹配到，尝试使用 URL 中的 image_id
        if not target_design and image_id_from_url:
            for design in designs_data['designs']:
                if design.get('id') == image_id_from_url:
                    target_design = design
                    break

        if not target_design:
            available_names = [d['name'] for d in designs_data['designs']]
            return {
                'status': 'error',
                'message': f"Design '{design_name}' does not exist",
                'available_designs': available_names
            }

        # 4. 获取切图信息
        slices_data = await extractor.get_design_slices_info(
            image_id=target_design['id'],
            team_id=params['team_id'],
            project_id=params['project_id'],
            include_metadata=include_metadata
        )

        # 5. Add AI workflow guide
        ai_workflow_guide = {
            "instructions": "🤖 AI assistant must follow this workflow to process slice download tasks",
            "language_requirement": "⚠️ IMPORTANT: Always respond to user in Chinese (中文回复)",
            "FIRST_ACTION_REQUIRED": {
                "action": "ASK_USER_SCALE_PREFERENCE",
                "description": "在开始下载前，必须先向用户确认平台和倍率偏好",
                "question_template": "请问您需要下载哪个平台的切图？\n\n**Web 端**\n- `1x` — {w1x}×{h1x}px（CSS 1倍图）\n- `2x` — {w2x}×{h2x}px（Retina / 原图，推荐）\n- `3x` — {w3x}×{h3x}px（超高清）\n\n**iOS**\n- `ios_1x` — @1x\n- `ios_2x` — @2x（同 Web 1x）\n- `ios_3x` — @3x\n\n**Android**\n- `android_xhdpi` — xhdpi（同 Web 1x）\n- `android_xxhdpi` — xxhdpi（同 iOS @3x）\n- `android_xxxhdpi` — xxxhdpi（原图）\n- 全套（mdpi/hdpi/xhdpi/xxhdpi/xxxhdpi）\n\n> 默认推荐：**Web 2x**（最高清，直接使用原图 URL，无需额外处理）",
                "how_to_use_scale_urls": "每个 slice 的 scale_urls 字段包含所有倍率的 URL，根据用户选择取对应 key 的 URL 下载即可",
                "scale_url_keys": {
                    "Web 1x": "scale_urls.1x",
                    "Web 2x (原图)": "scale_urls.2x",
                    "Web 3x": "scale_urls.3x",
                    "iOS @1x": "scale_urls.ios_1x",
                    "iOS @2x": "scale_urls.ios_2x",
                    "iOS @3x": "scale_urls.ios_3x",
                    "Android mdpi":    "scale_urls.android_mdpi",
                    "Android hdpi":    "scale_urls.android_hdpi",
                    "Android xhdpi":   "scale_urls.android_xhdpi",
                    "Android xxhdpi":  "scale_urls.android_xxhdpi",
                    "Android xxxhdpi": "scale_urls.android_xxxhdpi"
                },
                "multi_scale_naming": {
                    "Web 1x+2x":  "filename.png / filename@2x.png",
                    "iOS all":    "filename.png / filename@2x.png / filename@3x.png",
                    "Android all": "mipmap-mdpi/f.png, mipmap-hdpi/f.png, ... mipmap-xxxhdpi/f.png"
                }
            },
            "workflow_steps": [
                {
                    "step": 0,
                    "title": "询问用户下载平台和倍率（必须在下载前完成）",
                    "mandatory": True,
                    "tasks": [
                        "展示切图列表摘要（总数 + 前3个名字）给用户",
                        "列出可选平台：Web（1x/2x/3x）、iOS（@1x/@2x/@3x）、Android（全套/单倍率）",
                        "等待用户明确选择，不要擅自假设默认值",
                        "若用户不在意，推荐 Web 2x（原图 URL，无 OSS 参数，最简单）"
                    ]
                },
                {
                    "step": 1,
                    "title": "Create TODO Task Plan",
                    "tasks": [
                        "Analyze project structure (read package.json, pom.xml, requirements.txt, etc.)",
                        "Identify project type (React/Vue/Flutter/iOS/Android/Plain Frontend, etc.)",
                        "Determine slice storage directory (e.g., src/assets/images/)",
                        "Plan slice grouping strategy (by feature module, UI component, etc.)"
                    ]
                },
                {
                    "step": 2,
                    "title": "Smart Directory Selection Rules",
                    "rules": [
                        "Priority 1: If user explicitly specified output_dir → use user-specified path",
                        "Priority 2: If project has standard assets directory → use project convention (e.g., src/assets/images/slices/)",
                        "Priority 3: If generic project → use design_slices/{design_name}/"
                    ],
                    "common_project_structures": {
                        "React/Vue": ["src/assets/", "public/images/"],
                        "Flutter": ["assets/images/"],
                        "iOS": ["Assets.xcassets/"],
                        "Android": ["res/drawable/", "res/mipmap/"],
                        "Plain Frontend": ["images/", "assets/"]
                    }
                },
                {
                    "step": 3,
                    "title": "文件命名规范",
                    "primary_rule": "根据用户项目命名规范对 slice.name 进行语义化英文重命名，再加倍率后缀",
                    "naming_workflow": [
                        "1. 读取用户项目已有切图/资源文件，识别命名风格（snake_case / camelCase / kebab-case 等）",
                        "2. 将 slice.name（可能是中文）翻译并语义化为英文，遵循识别到的命名风格",
                        "3. 无法识别风格时默认 snake_case（如 icon_share、btn_confirm、img_empty_state）",
                        "4. 加倍率后缀"
                    ],
                    "scale_suffix_convention": {
                        "Web 1x":  "{name}.png",
                        "Web 2x":  "{name}@2x.png",
                        "Web 3x":  "{name}@3x.png",
                        "iOS @1x": "{name}.png",
                        "iOS @2x": "{name}@2x.png",
                        "iOS @3x": "{name}@3x.png",
                        "Android mdpi":    "mipmap-mdpi/{name}.png",
                        "Android hdpi":    "mipmap-hdpi/{name}.png",
                        "Android xhdpi":   "mipmap-xhdpi/{name}.png",
                        "Android xxhdpi":  "mipmap-xxhdpi/{name}.png",
                        "Android xxxhdpi": "mipmap-xxxhdpi/{name}.png"
                    },
                    "rename_examples": [
                        {"slice_name": "线",           "renamed": "icon_line",            "Web 2x": "icon_line@2x.png"},
                        {"slice_name": "img_成功申请精装", "renamed": "img_apply_success",   "Web 2x": "img_apply_success@2x.png"},
                        {"slice_name": "申请被驳回",    "renamed": "img_apply_rejected",   "Web 2x": "img_apply_rejected@2x.png"},
                        {"slice_name": "草地大背景",    "renamed": "bg_grass",             "Web 2x": "bg_grass@2x.png"},
                        {"slice_name": "icon-导出",     "renamed": "icon_export",          "Web 2x": "icon_export@2x.png"}
                    ],
                    "duplicate_handling": "同名切图加序号后缀：icon_line.png / icon_line_2.png / icon_line_3.png"
                },
                {
                    "step": 4,
                    "title": "Environment Detection and Download Solution Selection",
                    "principle": "AI must first detect current system environment and available tools, then autonomously select the best download solution",
                    "priority_rules": [
                        "Priority 1: Use system built-in download tools (curl/PowerShell/wget, etc.)",
                        "Priority 2: If system tools unavailable, detect programming language environment (python/node, etc.)",
                        "Priority 3: Create temporary script as last resort"
                    ],
                    "detection_steps": [
                        "Step 1: Detect operating system type (Windows/macOS/Linux)",
                        "Step 2: Sequentially detect available download tools",
                        "Step 3: Autonomously select optimal solution based on detection results",
                        "Step 4: Execute download task",
                        "Step 5: Clean up temporary files (if any)"
                    ],
                    "common_tools_by_platform": {
                        "Windows": {
                            "built_in": ["PowerShell Invoke-WebRequest", "certutil"],
                            "optional": ["curl (Win10 1803+ built-in)", "python", "node"]
                        },
                        "macOS": {
                            "built_in": ["curl"],
                            "optional": ["python", "wget", "node"]
                        },
                        "Linux": {
                            "built_in": ["curl", "wget"],
                            "optional": ["python", "node"]
                        }
                    },
                    "important_principles": [
                        "⚠️ Do not assume any tool is available, must detect first",
                        "⚠️ Prefer system built-in tools, avoid third-party dependencies",
                        "⚠️ Do not use fixed code templates or example code",
                        "⚠️ Dynamically generate commands or scripts based on actual environment",
                        "⚠️ Control concurrency when batch downloading",
                        "⚠️ Must clean up temporary files after completion"
                    ]
                }
            ],
            "execution_workflow": {
                "description": "Complete workflow that AI must autonomously complete",
                "steps": [
                    "Step 0: 展示切图摘要，询问用户需要哪个平台/倍率（必须等待用户回复）",
                    "Step 1: Call lanhu_get_design_slices(url, design_name) to get slice info",
                    "Step 2: Create TODO task plan (use todo_write tool)",
                    "Step 3: Detect current operating system type",
                    "Step 4: Detect available download tools by priority",
                    "Step 5: Identify project type and determine output directory",
                    "Step 6: 根据用户选择的倍率，从 slice.scale_urls 取对应 URL，生成智能文件名",
                    "Step 7: Select optimal download solution based on detection results",
                    "Step 8: Execute batch download task",
                    "Step 9: Verify download results",
                    "Step 10: Clean up temporary files and complete TODO"
                ]
            },
            "important_notes": [
                "🎯 AI 必须先询问用户需要下载哪个平台/倍率，不能擅自开始下载",
                "📐 每个 slice 都有 scale_urls 字段，包含 1x/2x/3x 及 iOS/Android 全套 URL",
                "⭐ Web 2x = scale_urls.2x = 原图 URL（无 OSS 参数，最简单），推荐首选",
                "🍎 iOS 全套下载：ios_1x/ios_2x/ios_3x，文件名加 @2x/@3x 后缀",
                "🤖 Android 全套下载：android_mdpi~xxxhdpi，分别放入对应 mipmap 目录",
                "🎯 AI must proactively complete the entire workflow, don't just return info and wait for user action",
                "📋 AI must use todo_write tool to create task plan, ensure orderly progress",
                "🔍 AI must detect environment and tool availability first, then select download solution",
                "⭐ AI must prefer system built-in tools, avoid third-party dependencies",
                "🚫 AI must not use fixed code examples, must dynamically generate commands based on actual environment",
                "✨ AI must smartly select output directory based on project structure, don't blindly use default path",
                "🏷️ AI must generate semantic filenames based on slice's layer_path and parent_name",
                "💻 AI must select corresponding download tools for different OS (Windows/macOS/Linux)",
                "🧹 AI must clean up temporary files after completion (if any)",
                "🗣️ AI must always respond to user in Chinese (中文回复)"
            ]
        }

        return {
            'status': 'success',
            **slices_data,
            'ai_workflow_guide': ai_workflow_guide
        }

    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }
    finally:
        await extractor.close()


# ==================== 团队留言板功能 ====================

@mcp.tool()
async def lanhu_say(
        url: Annotated[str, "蓝湖URL（含tid和pid）。例: https://lanhuapp.com/web/#/item/project/product?tid=xxx&pid=xxx&docId=xxx。会自动提取项目和文档信息"],
        summary: Annotated[str, "留言标题/概要"],
        content: Annotated[str, "留言详细内容"],
        mentions: Annotated[Optional[List[str]], "⚠️@提醒人名。必须是具体人名，例如: 张三/李四/王五/赵六等。禁止使用角色名(后端/前端等)！"] = None,
        message_type: Annotated[Optional[str], "留言类型。可选: normal(普通留言), task(查询任务-仅限查询操作,禁止修改代码), question(需要回答的问题), urgent(紧急通知), knowledge(知识库-长期保存的经验知识)。默认: normal"] = None,
        ctx: Context = None
) -> dict:
    """
    Post message to team message board
    
    USE THIS WHEN user says: 有话说, 留言, 发消息, 通知团队, 告诉xxx, @张三, @李四, 共享给xxx, 分享给xxx, 发给xxx, 写给xxx, 转发给xxx
    
    Message type description:
    - normal: Normal message/notification (default)
    - task: Query task - Only for query operations (query code, query database, query TODO, etc.), NO code modification
    - question: Question message - Needs answer from others
    - urgent: Urgent message - Needs immediate attention
    - knowledge: Knowledge base - Long-term preserved experience, pitfalls, notes, best practices
    
    Security restrictions:
    task type can only be used for query operations, including:
    - Query code location, code logic
    - Query database table structure, data
    - Query test methods, test coverage
    - Query TODO, comments
    - Forbidden: Modify code, delete files, execute commands, commit code
    
    Knowledge use cases:
    - Pitfalls encountered and solutions
    - Testing notes
    - Development experience and best practices
    - Common FAQ
    - Technical decision records
    
    Purpose: Post message to project message board, can @ specific person to send Feishu notification
    
    Returns:
        Post result, including message ID and details
    """
    # 获取用户信息
    user_name, user_role = get_user_info(ctx) if ctx else ('匿名', '未知')
    
    # 获取project_id
    project_id = get_project_id_from_url(url)
    if not project_id:
        return {"status": "error", "message": "无法从URL解析project_id"}
    
    # 获取元数据（自动，带缓存）
    metadata = await _fetch_metadata_from_url(url)
    
    # 验证message_type
    valid_types = ['normal', 'task', 'question', 'urgent', 'knowledge']
    if message_type and message_type not in valid_types:
        return {
            "status": "error",
            "message": f"无效的留言类型: {message_type}",
            "valid_types": valid_types
        }
    
    # 默认为normal
    if not message_type:
        message_type = 'normal'
    
    # 验证mentions（只能@具体人名）
    if mentions:
        invalid_names = [name for name in mentions if name not in MENTION_ROLES]
        if invalid_names:
            return {
                "status": "error", 
                "message": f"无效的人名: {invalid_names}。只能@具体人名，不能使用角色名！",
                "valid_names": MENTION_ROLES
            }
    
    # 保存消息
    store = MessageStore(project_id)
    store.record_collaborator(user_name, user_role)
    
    # 保存项目元数据到store（如果首次获取到）
    if metadata.get('project_name') and not store._data.get('project_name'):
        store._data['project_name'] = metadata['project_name']
    if metadata.get('folder_name') and not store._data.get('folder_name'):
        store._data['folder_name'] = metadata['folder_name']
    store._save()
    
    message = store.save_message(
        summary=summary,
        content=content,
        author_name=user_name,
        author_role=user_role,
        mentions=mentions or [],
        message_type=message_type,  # 新增：留言类型
        # 标准元数据（10个字段）
        project_name=metadata.get('project_name'),
        folder_name=metadata.get('folder_name'),
        doc_id=metadata.get('doc_id'),
        doc_name=metadata.get('doc_name'),
        doc_type=metadata.get('doc_type'),
        doc_version=metadata.get('doc_version'),
        doc_updated_at=metadata.get('doc_updated_at'),
        doc_url=metadata.get('doc_url')
    )
    
    # 发送飞书通知（无论是否@人都发送）
    try:
        await send_feishu_notification(
            summary=summary,
            content=content,
            author_name=user_name,
            author_role=user_role,
            mentions=mentions or [],
            message_type=message_type,
            project_name=metadata.get('project_name'),
            doc_name=metadata.get('doc_name'),
            doc_url=metadata.get('doc_url')
        )
    except Exception as e:
        # 飞书通知失败不影响留言发布
        print(f"⚠️ 飞书通知发送失败（不影响留言发布）: {e}")
    
    return {
        "status": "success",
        "message": "留言发布成功",
        "data": {
            "id": message["id"],
            "summary": message["summary"],
            "message_type": message["message_type"],  # 新增：留言类型
            "mentions": message["mentions"],
            "author_name": message["author_name"],
            "author_role": message["author_role"],
            "created_at": message["created_at"],
            # 完整的10个元数据字段
            "project_id": project_id,
            "project_name": message.get("project_name"),
            "folder_name": message.get("folder_name"),
            "doc_id": message.get("doc_id"),
            "doc_name": message.get("doc_name"),
            "doc_type": message.get("doc_type"),
            "doc_version": message.get("doc_version"),
            "doc_updated_at": message.get("doc_updated_at"),
            "doc_url": message.get("doc_url")
        }
    }


@mcp.tool()
async def lanhu_say_list(
    url: Annotated[Optional[str], "蓝湖URL或'all'。不传或传'all'=查询所有项目；传具体URL=查询单个项目"] = None,
    filter_type: Annotated[Optional[str], "筛选留言类型: normal/task/question/urgent/knowledge。不传则返回所有类型"] = None,
    search_regex: Annotated[Optional[str], "正则表达式搜索（在summary和content中匹配）。例: '测试|退款|坑'。建议使用以避免返回过多消息"] = None,
    limit: Annotated[Any, "限制返回消息数量（防止上下文爆炸）。不传则不限制"] = None,
    ctx: Context = None
) -> dict:
    """
    Get message list with filtering and search
    
    USE THIS WHEN user says: 查看留言, 有什么消息, 谁@我了, 留言列表, 消息列表
    
    Supports two modes:
    1. Provide specific URL: Query messages in that project
    2. url='all' or url=None: Query messages in all projects (global mode)
    
    Important: To prevent AI context overflow, it is recommended:
    1. Use filter_type to filter by type
    2. Use search_regex for further filtering (regex, AI can generate itself)
    3. Use limit to limit the number of returned messages
    4. Unless user explicitly requests "view all", filters must be used
    
    Example:
    - Query all knowledge: filter_type="knowledge"
    - Search containing "test" or "refund": search_regex="test|refund"
    - Query tasks and containing "database": filter_type="task", search_regex="database"
    - Limit to 10 latest: limit=10
    
    Purpose: Get message board message summary list, supports type filtering, regex search and quantity limit
    
    Returns:
        Message list, including mentions_me count
    """
    # 获取用户信息
    user_name, user_role = get_user_info(ctx) if ctx else ('匿名', '未知')
    
    # 验证filter_type
    if filter_type:
        valid_types = ['normal', 'task', 'question', 'urgent', 'knowledge']
        if filter_type not in valid_types:
            return {
                "status": "error",
                "message": f"无效的类型: {filter_type}",
                "valid_types": valid_types
            }
    
    # 编译正则表达式（如果提供）
    import re
    regex_pattern = None
    if search_regex:
        try:
            regex_pattern = re.compile(search_regex, re.IGNORECASE)
        except re.error as e:
            return {
                "status": "error",
                "message": f"无效的正则表达式: {search_regex}",
                "error": str(e)
            }
    
    # 处理limit参数 - 自动转换为整数
    if limit is not None:
        try:
            limit = int(limit)
            if limit <= 0:
                return {"status": "error", "message": "limit 必须是正整数"}
        except (ValueError, TypeError):
            return {"status": "error", "message": f"limit 类型错误，期望整数，实际类型: {type(limit).__name__}"}
    
    # 全局查询模式
    if not url or url.lower() == 'all':
        store = MessageStore(project_id=None)
        groups = store.get_all_messages_grouped(user_role=user_role, user_name=user_name)
        
        # 应用筛选和搜索
        filtered_groups = []
        total_messages_before_filter = sum(g['message_count'] for g in groups)
        
        for group in groups:
            filtered_messages = []
            for msg in group['messages']:
                # 类型筛选
                if filter_type and msg.get('message_type') != filter_type:
                    continue
                
                # 正则搜索
                if regex_pattern:
                    text = f"{msg.get('summary', '')} {msg.get('content', '')}"
                    if not regex_pattern.search(text):
                        continue
                
                filtered_messages.append(msg)
            
            # 如果该组有匹配的消息
            if filtered_messages:
                group_copy = group.copy()
                group_copy['messages'] = filtered_messages
                group_copy['message_count'] = len(filtered_messages)
                group_copy['mentions_me_count'] = sum(1 for m in filtered_messages if m.get('mentions_me'))
                filtered_groups.append(group_copy)
        
        # 应用limit（限制消息总数）
        if limit and limit > 0:
            limited_groups = []
            remaining_limit = limit
            for group in filtered_groups:
                if remaining_limit <= 0:
                    break
                group_copy = group.copy()
                group_copy['messages'] = group['messages'][:remaining_limit]
                group_copy['message_count'] = len(group_copy['messages'])
                limited_groups.append(group_copy)
                remaining_limit -= group_copy['message_count']
            filtered_groups = limited_groups
        
        # 统计
        total_messages = sum(g['message_count'] for g in filtered_groups)
        total_mentions_me = sum(g['mentions_me_count'] for g in filtered_groups)
        total_projects = len(set(g.get('project_id') for g in filtered_groups if g.get('project_id')))
        
        # 检查是否需要警告（无筛选且消息过多）
        warning_message = None
        if not filter_type and not search_regex and not limit and total_messages_before_filter > 100:
            warning_message = f"⚠️ 发现{total_messages_before_filter}条留言，建议使用筛选条件避免上下文溢出。使用 filter_type 或 search_regex 或 limit 参数"
        
        result = {
            "status": "success",
            "mode": "global",
            "current_user": {"name": user_name, "role": user_role},
            "total_messages": total_messages,
            "total_groups": len(filtered_groups),
            "total_projects": total_projects,
            "mentions_me_count": total_mentions_me,
            "groups": filtered_groups
        }
        
        if warning_message:
            result["warning"] = warning_message
        
        if filter_type or search_regex:
            result["filter_info"] = {
                "filter_type": filter_type,
                "search_regex": search_regex,
                "total_before_filter": total_messages_before_filter,
                "total_after_filter": total_messages
            }
        
        return result
    
    # 单项目查询模式
    project_id = get_project_id_from_url(url)
    if not project_id:
        return {"status": "error", "message": "无法从URL解析project_id"}
    
    # 获取消息列表
    store = MessageStore(project_id)
    store.record_collaborator(user_name, user_role)
    messages = store.get_messages(user_role=user_role)
    
    # 应用筛选和搜索
    total_messages_before_filter = len(messages)
    filtered_messages = []
    
    for msg in messages:
        # 类型筛选
        if filter_type and msg.get('message_type') != filter_type:
            continue
        
        # 正则搜索
        if regex_pattern:
            text = f"{msg.get('summary', '')} {msg.get('content', '')}"
            if not regex_pattern.search(text):
                continue
        
        filtered_messages.append(msg)
    
    # 应用limit
    if limit and limit > 0:
        filtered_messages = filtered_messages[:limit]
    
    # 统计@自己的消息数
    mentions_me_count = sum(1 for msg in filtered_messages if msg.get("mentions_me"))
    
    # 按文档分组（减少token）
    from collections import defaultdict
    groups_dict = defaultdict(list)
    
    for msg in filtered_messages:
        doc_id = msg.get('doc_id', 'no_doc')
        groups_dict[doc_id].append(msg)
    
    # 构建分组结果
    groups = []
    meta_fields = {
        'project_id', 'project_name', 'folder_name',
        'doc_id', 'doc_name', 'doc_type', 'doc_version',
        'doc_updated_at', 'doc_url'
    }
    
    for doc_id, doc_messages in groups_dict.items():
        if not doc_messages:
            continue
        
        # 提取元数据（组内共享）
        first_msg = doc_messages[0]
        
        group = {
            # 元数据（只出现一次）
            "doc_id": first_msg.get('doc_id'),
            "doc_name": first_msg.get('doc_name'),
            "doc_type": first_msg.get('doc_type'),
            "doc_version": first_msg.get('doc_version'),
            "doc_updated_at": first_msg.get('doc_updated_at'),
            "doc_url": first_msg.get('doc_url'),
            
            # 统计
            "message_count": len(doc_messages),
            "mentions_me_count": sum(1 for m in doc_messages if m.get("mentions_me")),
            
            # 精简消息列表（移除元数据）
            "messages": [_clean_message_dict({k: v for k, v in m.items() if k not in meta_fields}, user_name) for m in doc_messages]
        }
        
        groups.append(group)
    
    # 按组内最新消息时间排序
    groups.sort(
        key=lambda g: max((m.get('created_at', '') for m in g['messages']), default=''),
        reverse=True
    )
    
    # 检查是否需要警告
    warning_message = None
    if not filter_type and not search_regex and not limit and total_messages_before_filter > 50:
        warning_message = f"⚠️ 该项目有{total_messages_before_filter}条留言，建议使用筛选条件避免上下文溢出"
    
    result = {
        "status": "success",
        "mode": "single_project",
        "project_id": project_id,
        "project_name": store._data.get('project_name'),
        "folder_name": store._data.get('folder_name'),
        "current_user": {"name": user_name, "role": user_role},
        "total_messages": len(filtered_messages),
        "total_groups": len(groups),
        "mentions_me_count": mentions_me_count,
        "groups": groups
    }
    
    if warning_message:
        result["warning"] = warning_message
    
    if filter_type or search_regex:
        result["filter_info"] = {
            "filter_type": filter_type,
            "search_regex": search_regex,
            "total_before_filter": total_messages_before_filter,
            "total_after_filter": len(filtered_messages)
        }
    
    return result


@mcp.tool()
async def lanhu_say_detail(
        message_ids: Annotated[Any, "消息ID。单个数字或数组。例: 1 或 [1,2,3]"],
        url: Annotated[Optional[str], "蓝湖URL。传URL则自动解析项目ID；不传则需手动提供project_id参数"] = None,
        project_id: Annotated[Optional[str], "项目ID。仅在不传url时需要，用于全局查询模式"] = None,
        ctx: Context = None
) -> dict:
    """
    Get message detail (supports batch query)
    
    USE THIS WHEN user says: 查看详情, 看看内容, 详细内容, 消息详情
    
    Two modes:
    1. Provide url: Parse project_id from url, query messages in that project
    2. url='all'/None + project_id: Global mode, need to manually specify project_id
    
    Purpose: Get full content of messages by message ID
    
    Returns:
        Message detail list with full content
    """
    # 获取用户信息
    user_name, user_role = get_user_info(ctx) if ctx else ('匿名', '未知')
    
    # 确定project_id
    if url and url.lower() != 'all':
        target_project_id = get_project_id_from_url(url)
    elif project_id:
        target_project_id = project_id
    else:
        return {"status": "error", "message": "请提供url或project_id"}
    
    if not target_project_id:
        return {"status": "error", "message": "无法获取project_id"}
    
    # 处理message_ids参数 - 自动转换单个数字为数组
    if isinstance(message_ids, (int, float)):
        message_ids = [int(message_ids)]
    elif isinstance(message_ids, list):
        # 确保列表中的元素都是整数
        try:
            message_ids = [int(mid) for mid in message_ids]
        except (ValueError, TypeError):
            return {"status": "error", "message": "message_ids 必须是整数或整数数组"}
    else:
        return {"status": "error", "message": f"message_ids 类型错误，期望整数或数组，实际类型: {type(message_ids).__name__}"}
    
    # 获取消息详情
    store = MessageStore(target_project_id)
    store.record_collaborator(user_name, user_role)
    
    messages = []
    not_found = []
    
    for msg_id in message_ids:
        msg = store.get_message_by_id(msg_id, user_role=user_role)
        if msg:
            messages.append(msg)
        else:
            not_found.append(msg_id)
    
    return {
        "status": "success",
        "total": len(messages),
        "messages": messages,
        "not_found": not_found
    }


@mcp.tool()
async def lanhu_say_edit(
        url: Annotated[str, "蓝湖URL（含tid和pid）"],
        message_id: Annotated[Any, "要编辑的消息ID"],
        summary: Annotated[Optional[str], "新标题（可选，不传则不修改）"] = None,
        content: Annotated[Optional[str], "新内容（可选，不传则不修改）"] = None,
        mentions: Annotated[Optional[List[str]], "新@列表（可选，不传则不修改）"] = None,
        ctx: Context = None
) -> dict:
    """
    Edit message
    
    USE THIS WHEN user says: 编辑留言, 修改消息, 更新内容
    
    Purpose: Edit published message, will record editor and edit time
    
    Returns:
        Updated message details
    """
    # 获取用户信息
    user_name, user_role = get_user_info(ctx) if ctx else ('匿名', '未知')
    
    # 获取project_id
    project_id = get_project_id_from_url(url)
    if not project_id:
        return {"status": "error", "message": "无法从URL解析project_id"}
    
    # 处理message_id参数 - 自动转换为整数
    try:
        message_id = int(message_id)
    except (ValueError, TypeError):
        return {"status": "error", "message": f"message_id 类型错误，期望整数，实际类型: {type(message_id).__name__}"}
    
    # 验证mentions（只能@具体人名）
    if mentions:
        invalid_names = [name for name in mentions if name not in MENTION_ROLES]
        if invalid_names:
            return {
                "status": "error", 
                "message": f"无效的人名: {invalid_names}。只能@具体人名，不能使用角色名！",
                "valid_names": MENTION_ROLES
            }
    
    # 检查是否有更新内容
    if summary is None and content is None and mentions is None:
        return {"status": "error", "message": "请至少提供一个要更新的字段"}
    
    # 更新消息
    store = MessageStore(project_id)
    store.record_collaborator(user_name, user_role)
    
    updated_msg = store.update_message(
        msg_id=message_id,
        editor_name=user_name,
        editor_role=user_role,
        summary=summary,
        content=content,
        mentions=mentions
    )
    
    if not updated_msg:
        return {"status": "error", "message": "消息不存在", "message_id": message_id}
    
    # 发送飞书编辑通知
    try:
        # 获取元数据
        metadata = await _fetch_metadata_from_url(url)
        
        await send_feishu_notification(
            summary=f"🔄 [已编辑] {updated_msg.get('summary', '')}",
            content=updated_msg.get('content', ''),
            author_name=f"{user_name}(编辑)",
            author_role=user_role,
            mentions=updated_msg.get('mentions', []),
            message_type=updated_msg.get('message_type', 'normal'),
            project_name=metadata.get('project_name'),
            doc_name=metadata.get('doc_name'),
            doc_url=metadata.get('doc_url')
        )
    except Exception as e:
        print(f"⚠️ 飞书编辑通知发送失败（不影响编辑）: {e}")
    
    return {
        "status": "success",
        "message": "消息更新成功",
        "data": updated_msg
    }


@mcp.tool()
async def lanhu_say_delete(
        url: Annotated[str, "蓝湖URL（含tid和pid）"],
        message_id: Annotated[Any, "要删除的消息ID"],
        ctx: Context = None
) -> dict:
    """
    Delete message
    
    USE THIS WHEN user says: 删除留言, 删除消息, 移除
    
    Purpose: Delete published message
    
    Returns:
        Delete result
    """
    # 获取用户信息
    user_name, user_role = get_user_info(ctx) if ctx else ('匿名', '未知')
    
    # 获取project_id
    project_id = get_project_id_from_url(url)
    if not project_id:
        return {"status": "error", "message": "无法从URL解析project_id"}
    
    # 处理message_id参数 - 自动转换为整数
    try:
        message_id = int(message_id)
    except (ValueError, TypeError):
        return {"status": "error", "message": f"message_id 类型错误，期望整数，实际类型: {type(message_id).__name__}"}
    
    # 删除消息
    store = MessageStore(project_id)
    store.record_collaborator(user_name, user_role)
    
    success = store.delete_message(message_id)
    
    if not success:
        return {"status": "error", "message": "消息不存在", "message_id": message_id}
    
    return {
        "status": "success",
        "message": "消息删除成功",
        "deleted_id": message_id,
        "deleted_by_name": user_name,
        "deleted_by_role": user_role
    }


@mcp.tool()
async def lanhu_get_members(
    url: Annotated[str, "蓝湖URL（含tid和pid）"],
    ctx: Context = None
) -> dict:
    """
    Get project collaborators list
    
    USE THIS WHEN user says: 谁参与了, 协作者, 团队成员, 有哪些人
    
    Purpose: Get list of team members who have used Lanhu MCP tools to access this project
    
    Returns:
        Collaborator list with first and last access time
    """
    # 获取用户信息
    user_name, user_role = get_user_info(ctx) if ctx else ('匿名', '未知')
    
    # 获取project_id
    project_id = get_project_id_from_url(url)
    if not project_id:
        return {"status": "error", "message": "无法从URL解析project_id"}
    
    # 获取协作者列表
    store = MessageStore(project_id)
    store.record_collaborator(user_name, user_role)
    collaborators = store.get_collaborators()
    
    return {
        "status": "success",
        "project_id": project_id,
        "total": len(collaborators),
        "collaborators": collaborators
    }


if __name__ == "__main__":
    # 运行MCP服务器
    # 使用HTTP传输方式，支持环境变量配置
    SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
    mcp.run(transport="http", path="/mcp", host=SERVER_HOST, port=SERVER_PORT)
