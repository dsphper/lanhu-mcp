# 🎨 Lanhu MCP Server | 蓝湖MCP服务器

**lanhumcp | lanhu-mcp | Lanhu AI Integration | MCP Server for Lanhu**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)
[![FastMCP](https://img.shields.io/badge/FastMCP-Powered-orange.svg)](https://github.com/jlowin/fastmcp)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![GitHub Stars](https://img.shields.io/github/stars/dsphper/lanhu-mcp?style=social)](https://github.com/dsphper/lanhu-mcp/stargazers)
[![GitHub Issues](https://img.shields.io/github/issues/dsphper/lanhu-mcp)](https://github.com/dsphper/lanhu-mcp/issues)
[![GitHub Release](https://img.shields.io/github/v/release/dsphper/lanhu-mcp)](https://github.com/dsphper/lanhu-mcp/releases)
[![Code of Conduct](https://img.shields.io/badge/Contributor%20Covenant-2.0-4baaaa.svg)](CODE_OF_CONDUCT.md)

A powerful [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server for automatically extracting and analyzing Lanhu design documents, including Axure prototypes, UI designs, image slices, with built-in team collaboration message board.

**Perfect integration with:**

**International Mainstream AI IDEs**:
- ✅ **Cursor** - Cursor AI directly reads Lanhu requirements and designs
- ✅ **Windsurf** - Windsurf Cascade AI directly reads Lanhu documents
- ✅ **Claude Desktop** - Claude AI desktop app directly accesses Lanhu
- ✅ **Continue** - VSCode/JetBrains AI coding assistant
- ✅ **Cline** - Powerful VSCode AI programming plugin
- ✅ **GitHub Copilot Workspace** - GitHub AI development environment

**Chinese AI IDEs & Coding Assistants**:
- ✅ **ByteDance Trae** - China's first AI-native IDE (Doubao-1.5-pro)
- ✅ **Alibaba Tongyi Lingma** - AI assistant based on Tongyi model
- ✅ **Tencent CodeBuddy** - Full-cycle AI integrated workbench
- ✅ **Baidu Wenxin Kuaima** - Baidu AI coding assistant
- ✅ **Kuaishou KwaiCoder** - Kuaishou AI programming tool
- ✅ **Zhipu CodeGeeX** - Tsinghua-based AI coding assistant
- ✅ **Huawei Cloud CodeArts Snap** - Huawei Cloud AI assistant
- ✅ **SenseTime SenseCode** - SenseTime AI programming tool

**Any MCP-compatible AI development tools**

English | [简体中文](README.md)

## ✨ Key Features

**🔍 SEO Keywords**: lanhu mcp | lanhumcp | lanhu-mcp-server | lanhu ai | lanhu cursor | lanhu windsurf | lanhu claude | lanhu trae | lanhu tongyi | lanhu codebuddy | lanhu cline | lanhu continue | lanhu api | lanhu integration | lanhu axure | mcp server | model context protocol | ai requirement analysis | design collaboration tool | bytedance ai coding | alibaba ai coding | tencent ai coding | baidu ai coding

**Perfect for**: Product Managers | Frontend Developers | Backend Developers | QA Engineers | UI Designers | Cursor Users | Windsurf Users | Claude Users | Trae Users | Tongyi Lingma Users | CodeBuddy Users | Wenxin Kuaima Users | Cline Users | Continue Users | AI Coding Enthusiasts

### 📋 Requirement Document Analysis
- **Smart Document Extraction**: Automatically download and parse all pages, resources, and interactions from Axure prototypes
- **Three Analysis Modes**:
  - 🔧 **Developer Perspective**: Detailed field rules, business logic, global flowcharts
  - 🧪 **Tester Perspective**: Test scenarios, test cases, boundary values, validation rules
  - 🚀 **Quick Explorer**: Core function overview, module dependencies, review points
- **Four-Stage Workflow**: Global scan → Grouped analysis → Reverse validation → Generate deliverables
- **Zero Omission Guarantee**: TODO-driven systematic analysis process

### 🎨 UI Design Support
- **Design Viewing**: Batch download and display UI design images
- **Slice Extraction**: Automatically identify and export design slices and icon resources
- **Smart Naming**: Auto-generate semantic filenames based on layer paths

### 💬 Team Collaboration Board - Breaking AI IDE Silos
> 🌟 **Core Innovation**: Enable all developers' AI assistants to share team knowledge and context

**Problem Background**:
- Each developer's AI IDE (Cursor, Windsurf) is isolated, cannot share context
- Pitfall encountered by Developer A is unknown to Developer B's AI
- Requirement analysis results cannot be passed to Tester's AI
- Team knowledge is fragmented across chat windows, cannot be accumulated

**Innovative Solution**:
- 🔗 **Unified Knowledge Base**: All AI assistants connect to the same MCP server, sharing message board data
- 🧠 **Context Transfer**: Requirements analyzed by Developer's AI can be directly queried by Tester's AI
- 💡 **Knowledge Accumulation**: Pitfalls, experiences, best practices saved permanently as "Knowledge Base" type
- 📋 **Task Collaboration**: Use "Task" type messages to let AI help query code and database
- 📨 **@Mention Mechanism**: Support Feishu notifications, bridging AI collaboration and human communication
- 👥 **Collaborator Tracking**: Auto-record which team member's AI accessed which documents, full transparency

### ⚡ Performance Optimization
- **Smart Caching**: Permanent cache mechanism based on document version numbers
- **Incremental Updates**: Only download changed resources
- **Concurrent Processing**: Support batch page screenshots and resource downloads

## 🚀 Quick Start

> ⚠️ **IMPORTANT: Vision-Capable AI Model Required!**
>
> This project requires AI models with **image recognition and analysis capabilities**. Recommended 2025 mainstream vision models:
> - 🤖 **Claude** (Anthropic)
> - 🌟 **GPT** (OpenAI)
> - 💎 **Gemini** (Google)
> - 🚀 **Kimi** (Moonshot AI)
> - 🎯 **Qwen** (Alibaba)
> - 🧠 **DeepSeek** (DeepSeek)
>
> Text-only models (e.g., GPT-3.5, Claude Instant) are NOT supported.

---

### Prerequisites

- Python 3.10+
- Docker (optional, for containerized deployment)

### Installation

```bash
# Clone the repository
git clone https://github.com/dsphper/lanhu-mcp.git
cd lanhu-mcp

# Install dependencies
pip install -r requirements.txt

# Or use uv (recommended)
uv pip install -r requirements.txt
```

### Configuration

1. **Set Lanhu Cookie** (Required)

```bash
export LANHU_COOKIE="your_lanhu_cookie_here"
```

> 💡 Get Cookie: Log in to Lanhu web version, open browser developer tools, and copy Cookie from request headers

2. **Configure Feishu Bot** (Optional)

**Method 1: Environment Variable (Recommended, Docker-friendly)**
```bash
export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook-url"
```

**Method 2: Modify Code**
Modify in `lanhu_mcp_server.py`:
```python
DEFAULT_FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook-url"
```

3. **Configure User Mapping** (Optional)

Update `FEISHU_USER_ID_MAP` dictionary to support @mention feature.

4. **Other Environment Variables** (Optional)

```bash
# Server Configuration
export SERVER_HOST="0.0.0.0"       # Server listen address
export SERVER_PORT=8000            # Server port

# Data Storage
export DATA_DIR="./data"           # Data storage directory

# Performance Tuning
export HTTP_TIMEOUT=30             # HTTP request timeout (seconds)
export VIEWPORT_WIDTH=1920         # Browser viewport width
export VIEWPORT_HEIGHT=1080        # Browser viewport height

# Debug Options
export DEBUG="false"               # Debug mode (true/false)
```

> 📝 For complete environment variable documentation, see `config.example.env`

### Running

**Method 1: Direct Run**

```bash
python lanhu_mcp_server.py
```

Server will start at `http://localhost:8000/mcp`.

**Method 2: Docker Deployment**

```bash
docker build -t lanhu-mcp-server .
docker run -p 8000:8000 \
  -e LANHU_COOKIE="your_cookie" \
  -e FEISHU_WEBHOOK_URL="your_feishu_webhook_url" \
  -v $(pwd)/data:/app/data \
  lanhu-mcp-server
```

Or use docker-compose:

```bash
# Edit environment variables in docker-compose.yml
docker-compose up -d
```

### Connect to AI Client

Configure in MCP-compatible AI clients (e.g., Claude Code, Cursor, Windsurf):

**Cursor Configuration Example:**
```json
{
  "mcpServers": {
    "lanhu": {
      "url": "http://localhost:8000/mcp?role=Backend&name=John"
    }
  }
}
```

> 📌 URL Parameters:
> - `role`: User role (Backend/Frontend/Tester/Product, etc.)
> - `name`: User name (for collaboration tracking and @mentions)

## 🎯 Team Message Board: Breaking the Last Mile of AI Collaboration

### Why Do We Need a Team Message Board?

In the AI programming era, every developer has their own AI assistant (Cursor, Windsurf, Claude Code). But this brings a **serious problem**:

```
🤔 Pain Point Scenario:
┌─────────────────────────────────────────────┐
│ Backend Developer Wang's AI:                 │
│ "I've analyzed the login API requirements,   │
│  field validation rules are clear, starting  │
│  to write code..."                           │
└─────────────────────────────────────────────┘
                  ❌ Context Gap
┌─────────────────────────────────────────────┐
│ Tester Li's AI:                              │
│ "What? Login API? Let me read the           │
│  requirements again... What do these field   │
│  rules mean? How to test boundary values?"   │
└─────────────────────────────────────────────┘
```

**Every AI is doing repetitive work, unable to reuse analysis results from other AIs!**

### How Does Team Message Board Solve This?

**Design Philosophy: Connect all AI assistants to the same "brain"**

```
          ┌─────────────────────────────┐
          │   Lanhu MCP Server          │
          │   (Unified Knowledge Hub)    │
          │                             │
          │  📊 Requirement Analysis     │
          │  🐛 Development Pitfalls     │
          │  📋 Test Case Templates      │
          │  💡 Technical Decisions      │
          └──────────┬──────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
   ┌────▼───┐   ┌───▼────┐   ┌──▼─────┐
   │Backend │   │Frontend│   │Tester  │
   │  AI    │   │   AI   │   │  AI    │
   └────────┘   └────────┘   └────────┘
     Cursor      Windsurf     Claude
```

### Core Use Cases

#### Scenario 1: Sharing Requirement Analysis Results

**Backend AI (Wang) after analyzing requirements:**
```
@Tester_Li @Frontend_Zhang I've analyzed "User Login" requirements, key info:
- Phone required, 11 digits
- Password 6-20 chars, must include letters+numbers
- Verification code 4 digits, valid for 5 minutes
- Lock account for 30 min after 3 failed attempts

[Message Type: knowledge]
```

**Tester AI (Li) queries:**
```
AI: Query all knowledge base messages about "login"
→ Immediately get Wang's AI analysis results, no need to re-read requirements!
```

#### Scenario 2: Development Pitfall Records

**Backend AI (Wang) encounters issue:**
```
[Knowledge Base] Redis Connection Timeout Resolved

Issue: Production Redis frequent timeouts
Cause: Connection pool misconfiguration, maxIdle too small
Solution: Adjust to maxTotal=20, maxIdle=10

[Message Type: knowledge]
```

**Other developers' AI encounter same issue:**
```
AI: Search "Redis timeout" in knowledge base
→ Find solution, avoid repeating mistakes!
```

#### Scenario 3: Cross-Role Task Collaboration

**Product Manager's AI initiates query task:**
```
@Backend_Wang Please check how many test records in user table?

[Message Type: task]  // ⚠️ Safety: Read-only, no modifications
```

**Backend AI (Wang) sees notification:**
```
AI: Someone mentioned me, view details
→ Execute SELECT COUNT(*) FROM user WHERE status='test'
→ Reply: Total 1234 test records
```

#### Scenario 4: Urgent Issue Broadcast

**DevOps AI discovers production issue:**
```
🚨 URGENT: Production payment API error, investigate immediately!

Time: 2025-01-15 14:30
Symptom: Payment success rate dropped from 99% to 60%
Impact: About 200 orders affected

@Everyone

[Message Type: urgent]
→ Auto-send Feishu notification to all
```

### Message Type Design

| Type | Purpose | Search Strategy | Lifecycle |
|------|---------|----------------|-----------|
| 📢 **normal** | General notification | Time-based decay | Archive after 7 days |
| 📋 **task** | Query task (Safe: read-only) | Archive after completion | Task lifecycle |
| ❓ **question** | Needs answer | Pin unanswered | Archive after answered |
| 🚨 **urgent** | Urgent notification | Force push | Downgrade after 24h |
| 💡 **knowledge** | **Knowledge Base (Core)** | **Permanent searchable** | **Permanent** |

### Security Mechanism

**Task Type Safety Restrictions:**
```python
✅ Allowed Query Operations:
- Query code location, logic
- Query database schema, data
- Query test methods, coverage
- Query TODO, comments

❌ Forbidden Dangerous Operations:
- Modify code
- Delete files
- Execute commands
- Commit code
```

### Search and Filtering

**Smart Search (Prevent Context Overflow):**
```python
# Scenario 1: Query all test-related knowledge
lanhu_say_list(
    url='all',  # Global search
    filter_type='knowledge',
    search_regex='test|unit test|integration',
    limit=20
)

# Scenario 2: Query urgent messages in a project
lanhu_say_list(
    url='project_url',
    filter_type='urgent',
    limit=10
)

# Scenario 3: Find unresolved questions
lanhu_say_list(
    url='all',
    filter_type='question',
    search_regex='pending|unresolved'
)
```

### Collaborator Tracking

**Auto-record team member access history:**
```python
lanhu_get_members(url='project_url')

Returns:
{
  "collaborators": [
    {
      "name": "Wang",
      "role": "Backend",
      "first_seen": "2025-01-10 09:00:00",
      "last_seen": "2025-01-15 16:30:00"
    },
    {
      "name": "Li",
      "role": "Tester",
      "first_seen": "2025-01-12 10:00:00",
      "last_seen": "2025-01-15 14:00:00"
    }
  ]
}

💡 Use Cases:
- Know which colleagues' AI viewed this requirement
- Discover potential collaborators
- Team transparency
```

### Feishu Notification Integration

**Bridge AI collaboration and human communication:**

```python
# AI auto-sends Feishu notification (when @someone)
lanhu_say(
    url='project_url',
    summary='Need your code review',
    content='Login module password encryption logic, please review',
    mentions=['Wang', 'Zhang']  # Must be real names
)

# Feishu group receives:
┌──────────────────────────────────┐
│ 📢 Lanhu Collaboration Notice     │
│                                  │
│ 👤 Publisher: Li (Tester)        │
│ 📨 Mentions: @Wang @Zhang         │
│ 🏷️ Type: normal                  │
│ 📁 Project: User Center Redesign  │
│ 📄 Document: Login Module         │
│                                  │
│ 📝 Content:                      │
│ Login module password encryption  │
│ logic, please review              │
│                                  │
│ 🔗 View Requirement Doc           │
└──────────────────────────────────┘
```

### Technical Advantages

1. **Zero Learning Curve**: AI handles automatically, developers just chat naturally
2. **Real-time Sync**: All AI assistants connect to same data source
3. **Global Search**: Query knowledge base across projects
4. **Version Association**: Messages auto-link to document version
5. **Complete Metadata**: Auto-record 10 standard fields (project, doc, author, etc.)
6. **Smart Filtering**: Support regex search, type filtering, quantity limit (prevent token overflow)

---

## 📖 Usage Guide

### Requirement Document Analysis Workflow

**1. Get Page List**
```
Please help me analyze this requirement document:
https://lanhuapp.com/web/#/item/project/product?tid=xxx&pid=xxx&docId=xxx
```

**2. AI Automatically Executes Four-Stage Analysis**
- ✅ STAGE 1: Global text scan, build overall understanding
- ✅ STAGE 2: Grouped detailed analysis (based on selected mode)
- ✅ STAGE 3: Reverse validation, ensure zero omission
- ✅ STAGE 4: Generate deliverables (Requirement doc/Test plan/Review PPT)

**3. Get Deliverables**
- Developer Perspective: Detailed requirement doc + Global business flowchart
- Tester Perspective: Test plan + Test case list + Field validation table
- Quick Explorer: Review doc + Module dependency diagram + Discussion points

### UI Design Viewing

```
Please show me this design:
https://lanhuapp.com/web/#/item/project/stage?tid=xxx&pid=xxx
```

### Slice Download

```
Download all slices from "Homepage Design"
```

AI will automatically:
1. Detect project type (React/Vue/Flutter, etc.)
2. Select appropriate output directory
3. Generate semantic filenames
4. Batch download slices

### Team Messages

**Post Message:**
```
@John @Alice Need to confirm the password validation rules for login page
```

**View Messages:**
```
Show all messages that mention me
```

**Filtered Query:**
```
Show all knowledge base messages about "testing"
```

## 🛠️ Available Tools

| Tool Name | Description | Use Case |
|-----------|-------------|----------|
| `lanhu_resolve_invite_link` | Parse invite link | When user provides share link |
| `lanhu_get_pages` | Get prototype page list | Must call before analyzing requirements |
| `lanhu_get_ai_analyze_page_result` | Analyze prototype page content | Extract requirement details |
| `lanhu_get_designs` | Get UI design list | Must call before viewing designs |
| `lanhu_get_ai_analyze_design_result` | Analyze UI designs | View design drafts |
| `lanhu_get_design_slices` | Get slice information | Download icons and assets |
| `lanhu_say` | Post message | Team collaboration, @mentions |
| `lanhu_say_list` | View message list | Query message history |
| `lanhu_say_detail` | View message details | View full content |
| `lanhu_say_edit` | Edit message | Modify published messages |
| `lanhu_say_delete` | Delete message | Remove messages |
| `lanhu_get_members` | View collaborators | View team members |

## 📁 Project Structure

```
lanhu-mcp-server/
├── lanhu_mcp_server.py          # Main server file
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Docker image
├── data/                         # Data storage directory
│   ├── messages/                 # Message data
│   ├── axure_extract_*/          # Axure resource cache
│   └── lanhu_designs/            # Design cache
├── logs/                         # Log files
└── README.md                     # This document
```

## 🔧 Advanced Configuration

### Custom Role Mapping

Modify `ROLE_MAPPING_RULES` in code to support more roles:

```python
ROLE_MAPPING_RULES = [
    (["backend", "server"], "Backend"),
    (["frontend", "web"], "Frontend"),
    # Add more rules...
]
```

### Cache Control

Cache directory is controlled by environment variable `DATA_DIR`:

```bash
export DATA_DIR="/path/to/cache"
```

### Feishu Notification Customization

Customize message format and style in `send_feishu_notification()` function.

## 🤖 AI Assistant Integration

This project is designed for AI assistants with built-in "ErGou" assistant persona:

- 🎯 **Smart Analysis**: Automatically identify document types and best analysis modes
- 📋 **TODO-Driven**: Systematic workflow based on task lists
- 🗣️ **Natural Interaction**: Friendly conversational experience
- ✨ **Proactive Service**: No manual operations needed, AI completes the full process

## 📊 Performance Metrics

- ⚡ Page Screenshot: ~2 seconds/page (with cache)
- 💾 Resource Download: Support resume and incremental updates
- 🔄 Cache Hit: Permanent cache based on version numbers
- 📦 Batch Processing: Support concurrent downloads and analysis

## 🐛 FAQ

<details>
<summary><b>Q: What if Cookie expires?</b></summary>

A: Re-login to Lanhu web version, get new Cookie and update environment variable or config file.
</details>

<details>
<summary><b>Q: Screenshot fails or shows blank?</b></summary>

A: Ensure Playwright browsers are installed:
```bash
playwright install chromium
```
</details>

<details>
<summary><b>Q: Feishu notification fails?</b></summary>

A: Check:
1. Webhook URL is correct
2. Feishu bot is added to the group
3. User ID mapping is correctly configured
</details>

<details>
<summary><b>Q: How to clear cache?</b></summary>

A: Delete corresponding cache files in `data/` directory. System will automatically re-download.
</details>

## 🔒 Security Notes

- ⚠️ **Cookie Security**: Do not commit config files containing cookies to public repositories
- 🔐 **Access Control**: Recommend deploying in intranet or configuring firewall rules
- 📝 **Data Privacy**: Message data is stored locally, please keep it safe

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork this repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

### Development Guide

```bash
# Install development dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/

# Code formatting
black lanhu_mcp_server.py
```

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [FastMCP](https://github.com/jlowin/fastmcp) - Excellent MCP server framework
- [Playwright](https://playwright.dev/) - Reliable browser automation tool
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) - HTML parsing tool
- Lanhu Team - Providing quality design collaboration platform

## 📮 Contact

- Submit Issue: [GitHub Issues](https://github.com/dsphper/lanhu-mcp/issues)
- Email: dsphper@gmail.com

## 🗺️ Roadmap

- [ ] Support more design platforms (Figma, Sketch)
- [ ] Web management interface
- [ ] More analysis dimensions (Effort estimation, Tech stack recommendations)
- [ ] Enterprise-level permission management
- [ ] API documentation auto-generation
- [ ] Internationalization support

---

<p align="center">
  If this project helps you, please give it a ⭐️
</p>

<p align="center">
  Made with ❤️ by the Lanhu MCP Team
</p>

---

## ⚠️ Disclaimer

This project (Lanhu MCP Server) is a **third-party open source project**, independently developed and maintained by community developers, and **is NOT an official Lanhu product**.

**Important Notes:**
- This project has no official affiliation or partnership with Lanhu (蓝湖) company
- This project interacts with the Lanhu platform through public web interfaces, without any unauthorized access
- Using this project requires you to have a legitimate Lanhu account and access permissions
- Please comply with Lanhu platform's terms of service and usage policies
- This project is for learning and research purposes only, users assume all risks of use
- Developers are not responsible for any data loss, account issues, or other damages caused by using this project

**Data and Privacy:**
- This project processes and caches data locally, and does not transmit your data to third-party servers
- Your Lanhu Cookie and project data are only stored in your local environment
- Please keep your credentials secure and do not share them with others

**Open Source License:**
- This project is licensed under the MIT License, provided "as is" without warranty of any kind
- See [LICENSE](LICENSE) file for details

If you have any questions or suggestions, please feel free to communicate with us through [GitHub Issues](https://github.com/dsphper/lanhu-mcp/issues).

---

## 🏷️ Tags

`lanhumcp` `lanhu-mcp` `lanhu-ai` `mcp-server` `cursor-plugin` `windsurf-integration` `claude-integration` `trae-integration` `tongyi-lingma` `codebuddy` `cline-plugin` `continue-plugin` `axure-automation` `requirement-analysis` `design-collaboration` `ai-development-tools` `model-context-protocol` `lanhu-api` `lanhu-cursor` `lanhu-windsurf` `lanhu-claude` `ai-coding-assistant` `design-handoff` `prototype-analysis` `bytedance-ai` `alibaba-ai` `tencent-ai` `baidu-ai`

---

## 🔍 Common Search Questions

- **How to connect Cursor AI with Lanhu?** → Use Lanhu MCP Server
- **Windsurf Lanhu integration?** → Configure this MCP server
- **Claude Code read Axure prototypes?** → Install Lanhu MCP
- **ByteDance Trae Lanhu connection?** → Use this MCP server
- **Alibaba Tongyi Lingma Lanhu integration?** → Configure Lanhu MCP
- **Tencent CodeBuddy support Lanhu?** → Connect via MCP protocol
- **Baidu Wenxin Kuaima integrate Lanhu?** → Use this project
- **Cline plugin access Lanhu?** → Configure MCP server
- **Lanhu API for AI tools?** → This project provides MCP interface
- **Automated slice extraction from Lanhu?** → Use slice tools in this project
- **AI automated test case generation?** → Use tester analysis mode
- **蓝湖 Cursor 集成？** → 安装 Lanhu MCP Server
- **如何让 AI 读取蓝湖需求？** → 使用本 MCP 服务器
- **字节 Trae 蓝湖连接？** → 配置本 MCP 服务器
- **通义灵码蓝湖集成？** → 使用 Lanhu MCP

---

<!-- Last checked: 2026-04-06 20:35 -->
