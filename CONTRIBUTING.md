# 贡献指南 / Contributing Guide

感谢您对 Lanhu MCP Server 项目的关注！我们欢迎任何形式的贡献。

Thank you for your interest in the Lanhu MCP Server project! We welcome all forms of contributions.

[English](#english) | [简体中文](#简体中文)

---

## 简体中文

### 🤝 如何贡献

#### 报告 Bug

如果您发现了 Bug，请通过 [GitHub Issues](https://github.com/dsphper/lanhu-mcp/issues) 提交,并包含以下信息：

- **Bug 描述**：清晰简洁的描述
- **复现步骤**：详细的复现步骤
- **期望行为**：您期望发生什么
- **实际行为**：实际发生了什么
- **环境信息**：
  - 操作系统和版本
  - Python 版本
  - 依赖版本（从 `pip list` 获取）
- **相关日志**：错误堆栈或日志信息
- **截图**（如适用）

#### 提出新功能

如果您有新功能的想法：

1. 先查看 [Issues](https://github.com/dsphper/lanhu-mcp/issues) 确认是否已有相关讨论
2. 创建一个新的 Feature Request Issue
3. 详细描述功能的使用场景和预期效果
4. 如果可能，提供实现思路

#### 提交代码

**准备工作：**

```bash
# 1. Fork 本仓库到您的账号

# 2. 克隆您的 Fork
git clone https://github.com/YOUR_USERNAME/lanhu-mcp.git
cd lanhu-mcp

# 3. 添加上游仓库
git remote add upstream https://github.com/dsphper/lanhu-mcp.git

# 4. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 5. 安装开发依赖
pip install -r requirements.txt
pip install black flake8 pytest pytest-cov
```

**开发流程：**

```bash
# 1. 创建功能分支
git checkout -b feature/your-feature-name

# 2. 进行开发
# ... 编写代码 ...

# 3. 代码格式化
black lanhu_mcp_server.py

# 4. 代码检查
flake8 lanhu_mcp_server.py --max-line-length=120

# 5. 运行测试（如果有）
pytest tests/ -v

# 6. 提交更改
git add .
git commit -m "feat: add amazing feature"

# 7. 推送到您的 Fork
git push origin feature/your-feature-name

# 8. 在 GitHub 上创建 Pull Request
```

**提交信息规范：**

我们使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

- `feat:` 新功能
- `fix:` Bug 修复
- `docs:` 文档更新
- `style:` 代码格式调整（不影响功能）
- `refactor:` 重构（既不是新功能也不是 Bug 修复）
- `perf:` 性能优化
- `test:` 测试相关
- `chore:` 构建过程或辅助工具的变动

**示例：**
```bash
feat: add support for Figma design import
fix: resolve cache invalidation issue when version changes
docs: update README with new configuration options
refactor: extract message store logic into separate class
```

### 📋 代码规范

#### Python 代码风格

- 遵循 [PEP 8](https://www.python.org/dev/peps/pep-0008/) 规范
- 使用 Black 进行自动格式化（行长度 120）
- 函数和类必须有文档字符串（docstring）
- 复杂逻辑需要添加注释

**示例：**

```python
async def fetch_metadata(url: str, use_cache: bool = True) -> dict:
    """
    从蓝湖URL获取元数据

    Args:
        url: 蓝湖文档URL
        use_cache: 是否使用缓存，默认为True

    Returns:
        包含元数据的字典

    Raises:
        ValueError: URL格式不正确时抛出
    """
    # 实现代码...
```

#### 命名约定

- 类名：`PascalCase` (例如：`MessageStore`, `LanhuExtractor`)
- 函数名：`snake_case` (例如：`get_pages_list`, `send_notification`)
- 常量：`UPPER_CASE` (例如：`BASE_URL`, `DEFAULT_COOKIE`)
- 私有成员：前缀 `_` (例如：`_load_cache`, `_metadata_cache`)

#### 错误处理

- 使用明确的异常类型
- 提供有意义的错误消息
- 记录错误日志

```python
try:
    response = await self.client.get(url)
    response.raise_for_status()
except httpx.HTTPStatusError as e:
    logger.error(f"HTTP error occurred: {e}")
    raise ValueError(f"Failed to fetch data from {url}: {e.response.status_code}")
```

### 🧪 测试

如果您添加了新功能，请编写相应的测试：

```python
# tests/test_message_store.py
import pytest
from lanhu_mcp_server import MessageStore

def test_save_message():
    """测试消息保存功能"""
    store = MessageStore("test_project")
    msg = store.save_message(
        summary="Test message",
        content="Test content",
        author_name="Test User",
        author_role="Developer"
    )

    assert msg["id"] == 1
    assert msg["summary"] == "Test message"
    assert msg["author_name"] == "Test User"
```

### 📖 文档

如果您更改了 API 或添加了新功能，请更新相关文档：

- 更新 README.md
- 更新工具的 docstring
- 添加使用示例
- 更新英文文档（README_EN.md）

### 🔍 代码审查

所有 Pull Request 都需要经过代码审查。请确保：

- ✅ 代码通过所有 CI 检查
- ✅ 遵循项目代码规范
- ✅ 有完整的提交信息
- ✅ 有相关的测试（如适用）
- ✅ 文档已更新（如适用）

### ⚠️ 安全注意事项

- **不要**提交包含真实 Cookie 的代码
- **不要**提交包含真实 API 密钥的代码
- **不要**提交包含用户隐私数据的代码
- 使用环境变量或配置文件处理敏感信息
- 在提交前检查 `.gitignore` 是否正确配置

---

## English

### 🤝 How to Contribute

#### Report Bugs

If you find a bug, please submit it through [GitHub Issues](https://github.com/dsphper/lanhu-mcp/issues) with the following information:

- **Bug Description**: Clear and concise description
- **Reproduction Steps**: Detailed steps to reproduce
- **Expected Behavior**: What you expected to happen
- **Actual Behavior**: What actually happened
- **Environment Info**:
  - OS and version
  - Python version
  - Dependencies versions (from `pip list`)
- **Related Logs**: Error stack or log information
- **Screenshots** (if applicable)

#### Suggest New Features

If you have ideas for new features:

1. Check [Issues](https://github.com/dsphper/lanhu-mcp/issues) to see if there's already a discussion
2. Create a new Feature Request Issue
3. Describe the use case and expected behavior in detail
4. Provide implementation ideas if possible

#### Submit Code

**Preparation:**

```bash
# 1. Fork this repository to your account

# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/lanhu-mcp.git
cd lanhu-mcp

# 3. Add upstream repository
git remote add upstream https://github.com/dsphper/lanhu-mcp.git

# 4. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 5. Install development dependencies
pip install -r requirements.txt
pip install black flake8 pytest pytest-cov
```

**Development Workflow:**

```bash
# 1. Create feature branch
git checkout -b feature/your-feature-name

# 2. Develop
# ... write code ...

# 3. Format code
black lanhu_mcp_server.py

# 4. Code linting
flake8 lanhu_mcp_server.py --max-line-length=120

# 5. Run tests (if available)
pytest tests/ -v

# 6. Commit changes
git add .
git commit -m "feat: add amazing feature"

# 7. Push to your fork
git push origin feature/your-feature-name

# 8. Create Pull Request on GitHub
```

**Commit Message Convention:**

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation update
- `style:` Code style change (no functionality change)
- `refactor:` Refactoring (neither feature nor bug fix)
- `perf:` Performance optimization
- `test:` Test-related
- `chore:` Build process or auxiliary tool changes

### 📋 Code Standards

#### Python Code Style

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use Black for auto-formatting (line length 120)
- Functions and classes must have docstrings
- Add comments for complex logic

#### Naming Conventions

- Class names: `PascalCase` (e.g., `MessageStore`, `LanhuExtractor`)
- Function names: `snake_case` (e.g., `get_pages_list`, `send_notification`)
- Constants: `UPPER_CASE` (e.g., `BASE_URL`, `DEFAULT_COOKIE`)
- Private members: prefix `_` (e.g., `_load_cache`, `_metadata_cache`)

### 🧪 Testing

If you add new features, please write corresponding tests.

### 📖 Documentation

If you change APIs or add new features, please update relevant documentation.

### ⚠️ Security Considerations

- **DO NOT** commit code with real Cookies
- **DO NOT** commit code with real API keys
- **DO NOT** commit code with user privacy data
- Use environment variables or config files for sensitive information
- Check `.gitignore` is properly configured before committing

---

## 📞 Questions?

If you have any questions, feel free to:

- Open a [Discussion](https://github.com/dsphper/lanhu-mcp/discussions)
- Join our community chat (if available)
- Email us at: dsphper@gmail.com

Thank you for contributing! 🎉

<!-- Last checked: 2026-04-03 08:51 -->
