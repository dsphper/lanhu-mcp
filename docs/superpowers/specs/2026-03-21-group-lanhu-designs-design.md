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
| 2 | R1: 状态后缀 | `[\-\–\—](展开|收起|已兑换|成功|失败|正常|禁用|选中|未选中|默认|悬停|按下|聚焦|错误|加载|空|满)$` | `登录-展开` → 状态=展开 |
| 3 | R2: 数字后缀 | `[_\s]*[–—_\-]?\s*(\d+)$` | `识别提示1` → 序号=1 |
| 4 | R3: 子页面/弹窗 | `[_\s]*[–—]+[_\s]*(.+)$` | `登录_–_隐私弹窗` → 子页面=隐私弹窗 |

### 2.2 状态关键词列表

```python
STATE_KEYWORDS = [
    # 交互状态
    '展开', '收起', '选中', '未选中', '默认', '悬停', '按下', '聚焦', '禁用',
    # 业务状态
    '已兑换', '成功', '失败', '正常', '错误', '加载', '空', '满',
    # 动作状态
    '进行中', '已完成', '待处理'
]
```

### 2.3 识别流程

```
输入: "02_登录-展开_–_隐私弹窗"

Step 1: R0 提取业务顺序
  → 业务顺序 = "02"
  → 剩余 = "登录-展开_–_隐私弹窗"

Step 2: R1 提取状态后缀
  → 状态 = "展开"
  → 剩余 = "登录_–_隐私弹窗"

Step 3: R2 提取数字后缀
  → 无匹配

Step 4: R3 提取子页面
  → 子页面 = "隐私弹窗"
  → 分组名 = "登录"

最终结果:
  业务顺序 = "02"
  分组名 = "登录"
  状态 = "展开"
  子页面 = "隐私弹窗"
  组内类型 = "弹窗"
```

---

## 3. 分组逻辑

### 3.1 分组键生成

```python
def generate_group_key(name: str) -> tuple[str, str, str]:
    """
    生成分组键

    Returns:
        (业务顺序, 分组名, 组内类型)

    组内类型:
        - "main": 主页面
        - "popup": 弹窗
        - "state": 状态变体
        - "variant": 数字变体
    """
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

### 5.1 合并策略

1. **同名切图**: 保留最大尺寸版本
2. **尺寸记录**: 记录所有来源尺寸，标注保留版本
3. **来源追踪**: 添加来源页面列

### 5.2 冲突处理

```python
def merge_slices(slices_by_name: dict[str, list[Slice]]) -> list[Slice]:
    """
    合并同名切图

    Args:
        slices_by_name: 按名称分组的切图列表

    Returns:
        合并后的切图列表（每个名称只保留一个）
    """
    result = []
    for name, versions in slices_by_name.items():
        if len(versions) == 1:
            result.append(versions[0])
        else:
            # 保留最大尺寸
            largest = max(versions, key=lambda s: s.width * s.height)
            largest.sources = [(v.page_name, v.width, v.height) for v in versions]
            result.append(largest)
    return result
```

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
    └── merged_generator.py (生成合并文档)
        └── 依赖: analyze-lanhu-design 的 markdown_generator.py
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

- `test_name_parser.py`: 测试命名规则解析
- `test_page_grouper.py`: 测试分组逻辑
- `test_slice_merger.py`: 测试切图合并

### 8.2 集成测试

使用 `docs/lanhu/pages/DesignProject-da907f83-2026032023` 进行测试

预期分组:
- 识别提示: 6 个页面（识别提示、识别提示1-3、识别提示_–_1-2）
- 商品提货页: 4 个页面
- 长时间未操作: 3 个页面
- 礼品卡兑换: 3 个页面

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
