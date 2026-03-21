# Export Lanhu Skill - 增强功能设计规格

## 概述

为 export-lanhu skill 添加四项增强功能：
1. 设计图选择交互（组合模式）
2. 按关键词分组保存
3. 平台适配（iOS/Android/Web）
4. 切图格式和比例支持

## 需求背景

- **选择交互**：用户希望能在匹配结果中选择部分设计图导出
- **分组保存**：输出按关键词分组，便于管理
- **平台适配**：根据目标平台生成对应格式的资源
- **切图配置**：支持多种格式和比例

---

## 功能 1：设计图选择交互

### 选择语法

```
选择表达式          说明
─────────────────────────────────────────────
1,3,5              选择第 1、3、5 个
1-5                选择第 1 到 5 个
1-5,8,10           选择 1-5 和 8、10
1-5 -2,4          选择 1-5 但排除 2 和 4
*                  全选
^2,4              排除 2 和 4（全选后排除）
```

### 解析规则

```python
def parse_selection(expression: str, total_count: int) -> list[int]:
    """
    解析选择表达式

    Args:
        expression: 选择表达式
        total_count: 总数量

    Returns:
        选中的索引列表（0-based）

    Examples:
        "1,3,5" → [0, 2, 4]
        "1-5" → [0, 1, 2, 3, 4]
        "1-5 -2,4" → [0, 2]  # 1,3,5 (排除 2,4)
        "*" → [0, 1, ..., total_count-1]
        "^2,4" → 全选后排除 2,4
    """
```

### 交互流程

```
阶段 1：预览匹配结果
  🎯 匹配"登录"的设计图 (6/97)：

    [1] 2.2.登录-已输验证码 – 1
    [2] 01-登录-已输验证码状态
    [3] 01-登录-已输手机号状态
    [4] 助手登录页2
    [5] 01-登录-未输入状态
    [6] 助手登录页1

  📋 其他设计（91 个）：商品详情页轮播图...

阶段 2：选择
  请输入要导出的设计图（如 1-3,5 或 1-6 -4）：
  > 1-4

  ✅ 已选择 4 个设计图

阶段 3：确认导出
  是否导出这 4 个设计？
  [确认导出] [调整选择] [取消]
```

---

## 功能 2：按关键词分组保存

### 输出目录结构

```
{项目名}-{时间}/
├── designs/
│   ├── 登录/                    # 关键词分组
│   │   ├── 01-登录-未输入状态/
│   │   │   ├── schema.json
│   │   │   ├── sketch.json
│   │   │   └── preview.png
│   │   └── 01-登录-已输手机号状态/
│   ├── 注册/                    # 另一个关键词
│   │   └── ...
│   └── _其他/                   # 未匹配任何关键词的设计
│       └── ...
├── slices/
│   ├── iOS/                     # 按平台分组
│   │   └── 登录/                # 再按关键词分组
│   │       ├── 01-登录-未输入状态/
│   │       │   ├── icon@3x.png
│   │       │   └── banner@3x.webp
│   │       └── ...
│   ├── Android/
│   │   └── drawable-xxxhdpi/
│   │       └── 登录/
│   └── Web/
│       └── 登录/
├── meta.json
└── README.md
```

### 分组逻辑

```python
def get_design_group(design_name: str, keywords: list[str]) -> str:
    """
    根据设计名和关键词确定分组

    Args:
        design_name: 设计图名称
        keywords: 过滤关键词列表

    Returns:
        分组名称（空字符串表示不分组）
    """
    # 无关键词时，不分组
    if not keywords:
        return ""

    for keyword in keywords:
        if keyword.lower() in design_name.lower():
            return keyword
    return "_其他"


def get_design_output_path(base_dir: Path, design_name: str, keywords: list[str]) -> Path:
    """
    获取设计输出路径

    Args:
        base_dir: designs 基础目录
        design_name: 设计图名称
        keywords: 过滤关键词列表

    Returns:
        设计输出路径
    """
    group = get_design_group(design_name, keywords)

    if group:
        # 有关键词分组
        return base_dir / group / design_name
    else:
        # 无关键词，不分组
        return base_dir / design_name
```

### 分组策略表

| 场景 | 分组行为 | 输出路径示例 |
|------|----------|-------------|
| 有关键词，设计匹配 | 按关键词分组 | `designs/登录/01-登录页/` |
| 有关键词，设计不匹配 | 放入 _其他 | `designs/_其他/商品详情/` |
| **无关键词（导出全部）** | **不分组** | `designs/01-登录页/` |

---

## 功能 3：平台适配

### 平台配置表

| 特性 | iOS | Android | Web |
|------|-----|---------|-----|
| **标识符** | `ios` | `android` | `web` |
| **尺寸单位** | pt | dp | px |
| **切图倍率** | @2x, @3x | mdpi~xxxhdpi | @1x, @2x |
| **文件命名** | icon@3x.png | icon.png (在 drawable-xxxhdpi/) | icon@2x.png |
| **资源目录** | Assets.xcassets/ | res/drawable-*/ | assets/ |
| **默认倍率** | 3x | xxxhdpi (4x) | 2x |

### 倍率映射

```python
PLATFORM_SCALES = {
    'ios': {
        '1x': 1.0,
        '2x': 2.0,
        '3x': 3.0,
    },
    'android': {
        'mdpi': 1.0,
        'hdpi': 1.5,
        'xhdpi': 2.0,
        'xxhdpi': 3.0,
        'xxxhdpi': 4.0,
    },
    'web': {
        '1x': 1.0,
        '2x': 2.0,
    }
}

DEFAULT_SCALE = {
    'ios': '3x',
    'android': 'xxxhdpi',
    'web': '2x'
}
```

### 文件命名规则

```python
def get_slice_filename(name: str, platform: str, scale: str, format: str) -> str:
    """
    生成切图文件名

    Args:
        name: 切图名称
        platform: 平台 (ios/android/web)
        scale: 倍率
        format: 格式 (png/webp/svg)

    Returns:
        文件名
    """
    if platform == 'ios':
        return f"{name}@{scale}.{format}"
    elif platform == 'android':
        return f"{name}.{format}"  # 倍率体现在目录名
    else:  # web
        if scale == '1x':
            return f"{name}.{format}"
        return f"{name}@{scale}.{format}"
```

### 资源目录结构

```python
def get_slice_output_path(
    base_dir: Path,
    platform: str,
    keyword: str,
    design_name: str,
    scale: str,
    filename: str
) -> Path:
    """
    生成切图输出路径

    iOS:    slices/iOS/登录/设计名/icon@3x.png
    Android: slices/Android/drawable-xxxhdpi/登录/设计名/icon.png
    Web:    slices/Web/登录/设计名/icon@2x.png
    """
    if platform == 'ios':
        return base_dir / 'iOS' / keyword / design_name / filename
    elif platform == 'android':
        scale_dir = f"drawable-{scale}"
        return base_dir / 'Android' / scale_dir / keyword / design_name / filename
    else:  # web
        return base_dir / 'Web' / keyword / design_name / filename
```

---

## 功能 4：切图格式和比例

### 支持的格式

| 格式 | 说明 | 来源 |
|------|------|------|
| PNG | 无损位图，默认格式 | 蓝湖 API 直接提供 |
| WebP | 现代格式，压缩率高 | 从 PNG 转换 (Pillow) |
| SVG | 矢量格式 | 蓝湖 API 直接提供 |
| JPG | 有损压缩 | 从 PNG 转换 (Pillow) |

### 格式转换

```python
from PIL import Image
import io

def convert_format(png_data: bytes, target_format: str, quality: int = 85) -> bytes:
    """
    转换图片格式

    Args:
        png_data: PNG 格式的图片数据
        target_format: 目标格式 (webp/jpg)
        quality: 压缩质量 (1-100)

    Returns:
        转换后的图片数据
    """
    img = Image.open(io.BytesIO(png_data))

    if target_format == 'webp':
        output = io.BytesIO()
        img.save(output, format='WEBP', quality=quality)
        return output.getvalue()
    elif target_format == 'jpg':
        # JPEG 不支持透明通道，需要转换
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality)
        return output.getvalue()

    return png_data
```

### 倍率处理

由于蓝湖 API 默认返回最大倍率的切图，我们采用"下载最大倍率，按需缩小"的策略：

```python
def resize_to_scale(img: Image.Image, target_scale: float, max_scale: float) -> Image.Image:
    """
    将最大倍率图片缩小到目标倍率

    Args:
        img: 原始图片（最大倍率）
        target_scale: 目标倍率 (1.0, 2.0, 3.0)
        max_scale: 最大倍率 (如 3.0 或 4.0)

    Returns:
        缩放后的图片
    """
    if target_scale >= max_scale:
        return img

    ratio = target_scale / max_scale
    new_size = (int(img.width * ratio), int(img.height * ratio))
    return img.resize(new_size, Image.Resampling.LANCZOS)
```

---

## 错误处理

### API 错误处理

| 错误场景 | 处理策略 |
|----------|----------|
| **网络超时** | 重试 3 次，指数退避 (1s, 2s, 4s)，失败后跳过并记录 |
| **认证失败** | 立即终止，提示用户检查 Cookie 配置 |
| **项目不存在** | 立即终止，提示 URL 无效或无权限 |
| **设计图不存在** | 跳过该设计，继续处理其他设计 |
| **切图资源 404** | 跳过该切图，记录警告日志 |

### 错误处理代码

```python
class LanhuExportError(Exception):
    """导出错误基类"""
    pass

class AuthenticationError(LanhuExportError):
    """认证失败"""
    pass

class NetworkError(LanhuExportError):
    """网络错误（可重试）"""
    pass

class ResourceNotFoundError(LanhuExportError):
    """资源不存在（跳过）"""
    pass


async def download_with_retry(
    client: httpx.AsyncClient,
    url: str,
    max_retries: int = 3,
    initial_delay: float = 1.0
) -> bytes:
    """
    带重试的下载

    Args:
        client: HTTP 客户端
        url: 下载 URL
        max_retries: 最大重试次数
        initial_delay: 初始延迟秒数

    Returns:
        下载的数据

    Raises:
        NetworkError: 重试耗尽后仍失败
    """
    delay = initial_delay
    last_error = None

    for attempt in range(max_retries):
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.content
        except httpx.TimeoutException as e:
            last_error = e
            print(f"  ⚠️ Timeout, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
            await asyncio.sleep(delay)
            delay *= 2  # 指数退避
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Authentication failed. Please check your Cookie.")
            if e.response.status_code == 404:
                raise ResourceNotFoundError(f"Resource not found: {url}")
            raise NetworkError(f"HTTP error: {e}")

    raise NetworkError(f"Failed after {max_retries} retries: {last_error}")
```

### 格式转换错误处理

```python
class FormatConversionError(LanhuExportError):
    """格式转换失败"""
    pass


async def download_and_convert(
    client: httpx.AsyncClient,
    url: str,
    target_format: str,
    quality: int = 85
) -> tuple[bytes, str]:
    """
    下载并转换格式

    Args:
        client: HTTP 客户端
        url: 原始图片 URL
        target_format: 目标格式 (png/webp/jpg/svg)
        quality: 压缩质量

    Returns:
        (图片数据, 实际格式) 元组

    Note:
        转换失败时回退到原始 PNG 格式
    """
    # SVG 直接下载，无需转换
    if target_format == 'svg':
        try:
            data = await download_with_retry(client, url.replace('.png', '.svg'))
            return data, 'svg'
        except:
            raise ResourceNotFoundError("SVG format not available")

    # 下载 PNG
    png_data = await download_with_retry(client, url)

    if target_format == 'png':
        return png_data, 'png'

    # 转换格式
    try:
        converted = convert_format(png_data, target_format, quality)
        return converted, target_format
    except Exception as e:
        print(f"  ⚠️ Format conversion failed: {e}, falling back to PNG")
        return png_data, 'png'
```

### 导出结果统计

```python
@dataclass
class ExportResult:
    """导出结果"""
    success: bool
    output_dir: Path
    designs_total: int = 0
    designs_success: int = 0
    designs_failed: int = 0
    slices_total: int = 0
    slices_success: int = 0
    slices_failed: int = 0
    errors: list[str] = field(default_factory=list)

    def add_error(self, error: str):
        """添加错误记录"""
        self.errors.append(error)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'success': self.success,
            'output_dir': str(self.output_dir),
            'designs': {
                'total': self.designs_total,
                'success': self.designs_success,
                'failed': self.designs_failed,
            },
            'slices': {
                'total': self.slices_total,
                'success': self.slices_success,
                'failed': self.slices_failed,
            },
            'errors': self.errors,
        }
```

---

## 命令行参数

### 新增参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--select` | string | - | 选择表达式，跳过交互 |
| `--platform` | string | ios | 目标平台 (ios/android/web) |
| `--scales` | string | all | 切图比例 (1x,2x,3x / all) |
| `--formats` | string | png | 切图格式 (png,webp,svg)，逗号分隔 |
| `--group-by` | string | keyword | 分组方式 (keyword) |

### 参数组合示例

```bash
# 导出登录相关设计，iOS平台，PNG格式
python export_lanhu.py "<URL>" --keyword 登录 --platform ios --formats png

# 导出全部设计，Android平台，PNG+WebP格式，所有倍率
python export_lanhu.py "<URL>" --platform android --formats png,webp --scales all

# 选择特定设计导出，跳过交互
python export_lanhu.py "<URL>" --keyword 登录 --select "1-4" --platform web

# 预览模式
python export_lanhu.py "<URL>" --keyword 登录 --list
```

---

## SKILL.md 交互流程

### 用户输入解析

```
用户输入: 导出蓝湖 <URL> 登录相关的页面，iOS平台，PNG格式

Claude 解析:
- URL: https://lanhuapp.com/...
- 关键词: ["登录"]
- 平台: iOS (默认)
- 格式: ["PNG"]
- 比例: all (默认)
```

### 执行流程

```
阶段 1: 预览
  执行: python export_lanhu.py "<URL>" --keyword 登录 --list
  展示匹配结果

阶段 2: 选择
  展示选择提示
  用户输入: 1-4

阶段 3: 导出
  执行: python export_lanhu.py "<URL>" --keyword 登录 --select "1-4" --platform ios --formats png
  显示下载进度

阶段 4: 结果
  展示输出目录结构
  显示统计信息
```

---

## 输出示例

### meta.json

```json
{
  "source_url": "https://lanhuapp.com/...",
  "project_name": "电商APP设计",
  "export_time": "2026-03-21T15:30:00",
  "platform": "ios",
  "keywords": ["登录"],
  "groups": {
    "登录": {
      "design_count": 4,
      "slice_count": 16
    }
  },
  "formats": ["png"],
  "scales": ["2x", "3x"],
  "total_design_count": 4,
  "total_slice_count": 32
}
```

### 目录结构

```
电商APP设计-2026032115/
├── designs/
│   └── 登录/
│       ├── 01-登录-未输入状态/
│       ├── 01-登录-已输手机号状态/
│       ├── 01-登录-已输验证码状态/
│       └── 2.2.登录-已输验证码 – 1/
├── slices/
│   └── iOS/
│       └── 登录/
│           ├── 01-登录-未输入状态/
│           │   ├── icon@2x.png
│           │   ├── icon@3x.png
│           │   └── banner@3x.webp
│           └── ...
├── meta.json
└── README.md
```

---

## 验收标准

1. **选择交互**
   - [ ] 支持组合选择语法 (1-5,8,10 -2,4)
   - [ ] 支持全选 (*) 和排除 (^)
   - [ ] 无效输入时有友好提示

2. **分组保存**
   - [ ] 设计图按关键词分子目录
   - [ ] 切图按平台+关键词分目录
   - [ ] 未匹配的设计放入 _其他 目录

3. **平台适配**
   - [ ] iOS 生成 @2x/@3x 文件
   - [ ] Android 生成 drawable-* 目录结构
   - [ ] Web 生成 @1x/@2x 文件
   - [ ] meta.json 记录平台信息

4. **切图格式**
   - [ ] PNG 格式直接下载
   - [ ] WebP 格式自动转换
   - [ ] SVG 格式直接下载
   - [ ] 支持多格式同时导出

5. **命令行参数**
   - [ ] --select 参数正常工作
   - [ ] --platform 参数正常工作
   - [ ] --scales 参数正常工作
   - [ ] --formats 参数正常工作

6. **向后兼容**
   - [ ] 无新参数时行为与原版一致
   - [ ] 现有 --list、--keyword、--ids 参数继续工作
