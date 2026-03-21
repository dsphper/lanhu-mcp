# group-lanhu-designs 技能设计文档

## 1. 概述

### 1.1 目的

创建 `group-lanhu-designs` 技能，自动识别并合并蓝湖设计数据中相关联的页面，将同一功能的不同状态、弹窗、子页面合并为一个分析单元，便于 Claude Code 更高效地还原页面。

### 1.2 背景

蓝湖设计导出数据中，一个完整的功能页面可能被拆分为多个设计图：
- 主页面 + 弹窗（如：登录页 + 隐私弹窗）
- 不同状态（如：商品提货页-展开 / 商品提货页-收起）
- 不同变体（如：识别提示1 / 识别提示2 / 识别提示3）

当前 `analyze-lanhu-design` 技能独立分析每个页面，无法识别页面间的关联关系。

### 1.3 成功标准

1. 能自动识别页面命名规则，正确分组关联页面
2. 合并后的分析文档结构清晰，便于 Claude Code 实现
3. 切图合并去重，保留最大尺寸
4. 支持业务顺序前缀排序

---

## 2. 命名规则识别

### 2.1 规则优先级

| 优先级 | 规则名称 | 正则模式 | 示例 |
|--------|---------|---------|------|
| 1 | R0: 业务顺序前缀 | `^(\d+)[_\-\.\s]*(.+)$` | `01_登录` → 顺序=01, 名称=登录 |
| 2 | R3: 子页面/弹窗 | `[_\s]*[–—]+[_\s]*(.+)$` | `登录_–_隐私弹窗` → 子页面=隐私弹窗 |
| 3 | R1: 状态后缀 | `[\-\–\—](展开|收起|商品已兑换|成功|失败|正常|禁用|选中|未选中|默认|悬停|按下|聚焦|错误|加载|空|满)$` | `登录-展开` → 状态=展开 |
| 4 | R2: 数字后缀 | `(\d+)$` | `识别提示1` → 序号=1 |

**重要**: R3 优先于 R1 和 R2，确保 `识别提示_–_1` 被识别为子页面而非数字变体。

### 2.2 状态关键词列表

```python
STATE_KEYWORDS = [
    # 交互状态
    '展开', '收起', '选中', '未选中', '默认', '悬停', '按下', '聚焦', '禁用',
    # 业务状态
    '商品已兑换', '已兑换', '成功', '失败', '正常', '错误', '加载', '空', '满',
    # 动作状态
    '进行中', '已完成', '待处理'
]
```

### 2.3 Unicode 规范化

所有页面名称在解析前进行 Unicode 规范化：

```python
import unicodedata

def normalize_name(name: str) -> str:
    """规范化页面名称，统一不同类型的破折号"""
    # NFKC 规范化
    name = unicodedata.normalize('NFKC', name)
    # 统一破折号为标准形式
    name = name.replace('–', '-').replace('—', '-')
    return name
```

### 2.4 识别流程

```
输入: "02_登录-展开_–_隐私弹窗"

Step 0: Unicode 规范化
  → "02_登录-展开_-_隐私弹窗"

Step 1: R0 提取业务顺序
  → 业务顺序 = "02"
  → 剩余 = "登录-展开_-_隐私弹窗"

Step 2: R3 提取子页面（优先于 R1/R2）
  → 子页面 = "隐私弹窗"
  → 剩余 = "登录-展开"

Step 3: R1 提取状态后缀
  → 状态 = "展开"
  → 分组名 = "登录"

Step 4: R2 提取数字后缀
  → 无匹配

最终结果:
  业务顺序 = "02"
  分组名 = "登录"
  状态 = "展开"
  子页面 = "隐私弹窗"
  组内类型 = "popup"
  分组键 = "02_登录"
```

### 2.5 冲突解决规则

| 情况 | 处理方式 |
|------|---------|
| 多规则匹配 | 按 R3 > R1 > R2 优先级处理 |
| `识别提示_–_1` vs `识别提示1` | `_–_` 优先，识别为子页面 |
| 相同分组名不同业务顺序 | 不同分组（如 `01_登录` 和 `02_登录` 是不同分组） |
| 尾部下划线（如 `提货申请成功_`） | 去除尾部下划线后重新解析 |
| 多个子页面分隔符（如 `礼品卡兑换_–低价值_高价值`） | 只取第一个分隔符后的内容作为子页面名 |

---

## 3. 分组逻辑

### 3.1 解析结果数据结构

```python
@dataclass
class ParsedPageName:
    """解析后的页面名称"""
    original: str           # 原始名称
    business_order: str | None  # 业务顺序（如 "01"）
    group_name: str         # 分组名（如 "登录"）
    state: str | None       # 状态（如 "展开"）
    sub_page: str | None    # 子页面名（如 "隐私弹窗"）
    variant: int | None     # 数字变体（如 1）

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
```

### 3.2 分组键生成算法

```python
def parse_page_name(name: str) -> ParsedPageName:
    """
    解析页面名称，返回结构化信息

    算法步骤:
    1. Unicode 规范化
    2. 提取业务顺序前缀 (R0)
    3. 提取子页面/弹窗 (R3) - 优先！
    4. 提取状态后缀 (R1)
    5. 提取数字后缀 (R2)
    6. 剩余部分作为分组名
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
    state_pattern = '|'.join(STATE_KEYWORDS)
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

### 3.2 组内排序规则

优先级从高到低：

1. **组内类型顺序**: 主页面(main) → 弹窗(popup) → 状态变体(state) → 数字变体(variant)
2. **弹窗顺序**: 按识别出的子页面名称字母序
3. **状态顺序**: 默认 → 悬停 → 按下 → 禁用 → 其他
4. **数字顺序**: 1 → 2 → 3 → ...

### 3.3 分组示例

输入页面列表:
```
01_登录
01_登录_–_隐私弹窗
01_登录-展开
02_首页
02_首页_–_搜索弹窗
识别提示
识别提示1
识别提示2
```

分组结果:
```json
{
  "01_登录": {
    "business_order": "01",
    "group_name": "登录",
    "pages": [
      {"name": "01_登录", "type": "main"},
      {"name": "01_登录_–_隐私弹窗", "type": "popup", "subtype": "隐私弹窗"},
      {"name": "01_登录-展开", "type": "state", "subtype": "展开"}
    ]
  },
  "02_首页": {
    "business_order": "02",
    "group_name": "首页",
    "pages": [
      {"name": "02_首页", "type": "main"},
      {"name": "02_首页_–_搜索弹窗", "type": "popup", "subtype": "搜索弹窗"}
    ]
  },
  "识别提示": {
    "business_order": null,
    "group_name": "识别提示",
    "pages": [
      {"name": "识别提示", "type": "main"},
      {"name": "识别提示1", "type": "variant", "subtype": "1"},
      {"name": "识别提示2", "type": "variant", "subtype": "2"}
    ]
  }
}
```

---

## 4. 输出结构

### 4.1 目录结构

```
docs/lanhu/pages/DesignProject-xxx/
├── designs/                    # 原始设计数据
│   ├── 01_登录/
│   │   └── sketch.json
│   ├── 01_登录_–_隐私弹窗/
│   │   └── sketch.json
│   └── ...
├── analysis/                   # 原始分析（analyze-lanhu-design 生成）
│   ├── 01_登录-layout.md
│   └── ...
└── grouped/                    # 合并输出
    ├── 01_登录/
    │   ├── 登录-合并分析.md     # 合并后的分析文档
    │   └── slices/              # 合并后的切图
    │       ├── 关闭按钮@3x.png
    │       └── ...
    ├── 02_首页/
    │   ├── 首页-合并分析.md
    │   └── slices/
    └── ...
```

### 4.2 合并分析文档结构

```markdown
# 01_登录 - 合并分析

## 业务信息

| 属性 | 值 |
|------|-----|
| 业务顺序 | 01 |
| 分组名称 | 登录 |
| 包含页面 | 登录(主)、隐私弹窗、展开状态 |

---

## 主页面: 登录

### 设备信息
| 属性 | 值 |
|------|-----|
| 设备 | iOS @1x |
| 尺寸 | 375 x 812 |

### 图层结构
```
+-- [A] 登录 (375x812)
    +-- [#] 背景 (375x812)
    +-- [G] 表单 (300x200)
    ...
```

### Flex 布局建议
```css
.login {
  display: flex;
  flex-direction: column;
  ...
}
```

---

## 弹窗: 隐私弹窗

### 弹窗信息
| 属性 | 值 |
|------|-----|
| 尺寸 | 320 x 280 |
| 类型 | 模态弹窗 |

### 弹窗布局
...

---

## 变体: 展开状态

### 状态差异
- 原始状态: 表单收起
- 展开状态: 表单展开，高度增加 120px

---

## 合并切图索引

| 名称 | 尺寸 | 来源页面 | 备注 |
|------|------|---------|------|
| 关闭按钮 | 48x48 | 隐私弹窗 | |
| 背景图 | 375x812 | 登录 | 主页面背景 |
| ... | ... | ... | |

**总计**: 12 个切图（合并去重后）
```

---

## 5. 切图合并规则

### 5.1 Slice 数据结构

```python
@dataclass
class Slice:
    """切图资源"""
    name: str               # 切图名称（不含后缀）
    path: Path              # 文件路径
    width: int              # 宽度（像素）
    height: int             # 高度（像素）
    page_name: str          # 来源页面名称
    scale: float = 1.0      # 缩放比例（@1x/@2x/@3x）

    @property
    def area(self) -> int:
        """面积（用于尺寸比较）"""
        return self.width * self.height

    @property
    def base_name(self) -> str:
        """基础名称（去除 @2x/@3x 后缀）"""
        # 去除 @2x, @3x 等后缀
        return re.sub(r'@\d+x$', '', self.name)
```

### 5.2 合并策略

1. **同名切图**: 保留最大尺寸版本（按 `width * height` 比较）
2. **@2x/@3x 处理**: 视为同名切图，保留最高分辨率版本
3. **尺寸记录**: 记录所有来源尺寸，标注保留版本
4. **来源追踪**: 添加来源页面列

### 5.3 冲突处理

```python
def merge_slices(slices: list[Slice]) -> list[Slice]:
    """
    合并同名切图

    Args:
        slices: 所有切图列表

    Returns:
        合并后的切图列表（每个基础名称只保留一个）
    """
    # 按基础名称分组
    by_base_name: dict[str, list[Slice]] = {}
    for s in slices:
        base = s.base_name
        if base not in by_base_name:
            by_base_name[base] = []
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
```

### 5.4 尺寸比较规则

| 情况 | 比较方式 | 结果 |
|------|---------|------|
| 100x100 vs 50x50 | 面积: 10000 vs 2500 | 保留 100x100 |
| 100x50 vs 50x100 | 面积: 5000 vs 5000 | 保留第一个（稳定排序） |
| icon@1x vs icon@3x | 基础名相同，比较面积 | 保留 @3x |
| a.png vs a.jpg | 基础名相同 | 保留面积大的 |

---

## 6. 技术设计

### 6.1 模块结构

```
skills/group-lanhu-designs/
├── SKILL.md                    # 技能文档
├── scripts/
│   ├── group_designs.py        # 主入口脚本
│   ├── name_parser.py          # 命名规则解析器
│   ├── page_grouper.py         # 页面分组器
│   ├── slice_merger.py         # 切图合并器
│   └── merged_generator.py     # 合并文档生成器
└── references/
    └── naming-patterns.md      # 命名模式参考
```

### 6.2 依赖关系

```
group_designs.py (主入口)
    ├── name_parser.py (解析页面名称)
    ├── page_grouper.py (分组页面)
    │   └── 依赖: analyze-lanhu-design 的 models.py
    ├── slice_merger.py (合并切图)
    │   └── 定义: Slice dataclass（见 5.1 节）
    └── merged_generator.py (生成合并文档)
        └── 依赖: analyze-lanhu-design 的 markdown_generator.py
```

### 6.3 跨模块依赖说明

```python
# 在 group-lanhu-designs 脚本中导入 analyze-lanhu-design 的模块
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'analyze-lanhu-design' / 'scripts'))

from models import Layer, Style, Frame
from layer_parser import LayerParser
from markdown_generator import MarkdownGenerator
```

### 6.4 弹窗类型判断逻辑

```python
def detect_popup_type(layer: Layer) -> str:
    """
    检测弹窗类型

    Returns:
        - "modal": 模态弹窗（有遮罩层）
        - "toast": 轻提示（无遮罩，自动消失）
        - "drawer": 抽屉弹窗（从侧边滑出）
        - "popup": 普通弹窗
    """
    # 检查是否有半透明遮罩层
    for child in layer.children:
        if child.style and child.style.opacity and child.style.opacity < 0.3:
            # 有遮罩层，可能是模态弹窗
            if child.frame.width == layer.frame.width and child.frame.height == layer.frame.height:
                return "modal"

    # 检查弹窗尺寸和位置
    popup_width_ratio = layer.frame.width / 375  # 假设设计稿宽度 375
    if popup_width_ratio > 0.9:
        # 接近全屏，可能是抽屉
        if "抽屉" in layer.name or "drawer" in layer.name.lower():
            return "drawer"

    # 默认为普通弹窗
    return "popup"
```

### 6.3 命令行接口

```bash
# 基本用法
/group-lanhu-designs docs/lanhu/pages/DesignProject-xxx

# 指定输出目录
/group-lanhu-designs docs/lanhu/pages/DesignProject-xxx --output ./output/

# 指定框架
/group-lanhu-designs docs/lanhu/pages/DesignProject-xxx --framework flutter

# 仅分组不合并切图
/group-lanhu-designs docs/lanhu/pages/DesignProject-xxx --no-slices
```

---

## 7. 错误处理

### 7.1 边界情况

| 情况 | 处理方式 |
|------|---------|
| 无关联页面（单页面分组） | 正常输出，标记为独立页面 |
| 命名规则不匹配 | 作为独立页面处理 |
| 切图目录不存在 | 跳过切图合并，仅生成分析文档 |
| sketch.json 解析失败 | 记录错误，跳过该页面 |

### 7.2 日志输出

```
[INFO] 找到 27 个设计页面
[INFO] 识别到 8 个分组
[INFO] 分组 "01_登录": 3 个页面
[INFO] 分组 "02_首页": 2 个页面
[INFO] 独立页面: 12 个
[INFO] 切图合并: 156 → 89 (去重 67)
[INFO] 完成！输出目录: grouped/
```

---

## 8. 测试计划

### 8.1 单元测试

**test_name_parser.py**:
```python
def test_business_order_prefix():
    assert parse_page_name("01_登录").business_order == "01"
    assert parse_page_name("02-首页").business_order == "02"
    assert parse_page_name("登录").business_order is None

def test_state_suffix():
    assert parse_page_name("登录-展开").state == "展开"
    assert parse_page_name("商品提货页-商品已兑换").state == "商品已兑换"

def test_sub_page():
    assert parse_page_name("登录_–_隐私弹窗").sub_page == "隐私弹窗"
    assert parse_page_name("识别提示_–_1").sub_page == "1"
    assert parse_page_name("识别提示_–_1").page_type == "popup"

def test_variant():
    assert parse_page_name("识别提示1").variant == 1
    assert parse_page_name("识别提示2").variant == 2
    assert parse_page_name("识别提示").variant is None

def test_priority_r3_over_r2():
    # R3 优先于 R2，识别为子页面而非数字变体
    result = parse_page_name("识别提示_–_1")
    assert result.sub_page == "1"
    assert result.variant is None
    assert result.page_type == "popup"

def test_trailing_underscore():
    result = parse_page_name("提货申请成功_")
    assert result.group_name == "提货申请成功"
```

**test_page_grouper.py**:
```python
def test_group_key_generation():
    p1 = parse_page_name("01_登录")
    p2 = parse_page_name("01_登录_–_隐私弹窗")
    assert p1.group_key == p2.group_key == "01_登录"

def test_different_business_order_different_group():
    p1 = parse_page_name("01_登录")
    p2 = parse_page_name("02_登录")
    assert p1.group_key != p2.group_key

def test_intra_group_sorting():
    pages = ["01_登录-展开", "01_登录_–_隐私弹窗", "01_登录"]
    parsed = [parse_page_name(p) for p in pages]
    sorted_pages = sorted(parsed, key=lambda p: (TYPE_ORDER[p.page_type], p.sub_page or ""))
    assert sorted_pages[0].page_type == "main"
    assert sorted_pages[1].page_type == "popup"
```

**test_slice_merger.py**:
```python
def test_merge_same_name_slices():
    slices = [
        Slice("icon", Path("a/icon.png"), 48, 48, "登录"),
        Slice("icon", Path("b/icon@2x.png"), 96, 96, "弹窗"),
    ]
    merged = merge_slices(slices)
    assert len(merged) == 1
    assert merged[0].width == 96

def test_base_name_extraction():
    assert Slice("icon@2x", Path(), 48, 48, "").base_name == "icon"
    assert Slice("icon@3x", Path(), 72, 72, "").base_name == "icon"
```

### 8.2 集成测试

使用 `docs/lanhu/pages/DesignProject-da907f83-2026032023` 进行测试

**预期分组（27 个页面）**:

| 分组键 | 页面数 | 包含页面 |
|--------|--------|---------|
| `识别提示` | 6 | 识别提示(主)、识别提示1、识别提示2、识别提示3、识别提示_–_1、识别提示_–_2 |
| `商品提货页` | 4 | 商品提货页-展开、商品提货页-收起、商品提货页-商品已兑换、商品提货页_–商品组 |
| `长时间未操作` | 3 | 长时间未操作(主)、长时间未操作_–_1、长时间未操作_–_2 |
| `礼品卡兑换` | 3 | 礼品卡兑换_–低价值_高价值、礼品卡兑换_–高价值IOS、礼品卡兑换-商品已兑换 |
| `提货申请成功` | 2 | 提货申请成功_(主)、提货申请成功_–_1 |
| 独立页面 | 9 | APP引导页、便捷提货、我的、礼品详情、提货订单、支付成功、授权登录_–_4 等 |

**负面测试用例**:

| 测试场景 | 输入 | 预期结果 |
|---------|------|---------|
| 空目录 | `[]` | 返回空分组 |
| 全部独立页面 | `["首页", "我的", "设置"]` | 3 个独立分组 |
| 无效命名 | `["___", ""]` | 作为独立页面处理 |
| 特殊字符 | `["页面@#$%"]` | 作为独立页面处理 |

---

## 9. 后续扩展

### 9.1 可选功能

1. **自定义分组规则**: 支持用户配置文件覆盖默认规则
2. **交互流程图**: 生成分组内页面的交互流程图
3. **代码模板**: 基于分组生成 Vue/React 组件模板

### 9.2 版本规划

- v1.0: 基础分组和合并功能
- v1.1: 自定义分组规则支持
- v1.2: 交互流程图生成
