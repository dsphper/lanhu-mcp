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

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server for reading Lanhu design documents, Axure prototypes, UI designs and source assets, with a server-local team message board.

**MCP client integration:**

Client support depends on its MCP transport and image/resource capabilities. For visual design work, use a multimodal model and a client that can display MCP images and read resources.

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
- **Document Extraction**: Download and parse available pages and resources from Axure prototypes; interaction coverage depends on the source export
- **Three Analysis Modes**:
  - 🔧 **Developer Perspective**: Detailed field rules, business logic, global flowcharts
  - 🧪 **Tester Perspective**: Test scenarios, test cases, boundary values, validation rules
  - 🚀 **Quick Explorer**: Core function overview, module dependencies, review points
- **Four-Stage Workflow**: Global scan → Grouped analysis → Reverse validation → Generate deliverables
- **Coverage Tracking**: A task-based analysis workflow helps identify omissions; completeness still needs review

### 🎨 UI Design Support
- **Design Viewing**: Batch download and display UI design images
- **Versioned Visual Context — 1.8.0**: Pin a design snapshot, then inspect regions using a clean crop, a numbered overlay, stable node IDs and source styles
- **Original Asset Delivery**: Select designer exports separately from auxiliary renderings; download and verify files, then install a portable bundle in the frontend project
- **Source Format Selection**: Choose `original`, `prefer_svg` or `raster`; inspect available variants and explicit fallback results
- **Typography Evidence**: Read mixed-style UTF-16 text runs and font requirements; font availability remains unchecked and missing style properties remain explicit
- **Large Design Previews**: Use a preview bounded to a 4096-pixel long edge for oversized references, then request source-based regional detail where the image provider supports it

The model interprets component roles and chooses how to use assets. Python preserves IDs, geometry, source fields and files; it does not infer semantics from layer names or guarantee a finished page's visual accuracy. See [Visual design context and asset delivery](DESIGN_CONTEXT.md) for the full contract and limitations.

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
- **Versioned Caching**: Reuse cached document resources; the new visual tools keep separate design snapshots
- **Incremental Updates**: Only download changed resources
- **Concurrent Processing**: Support batch page screenshots and resource downloads

## 🚀 Quick Start

> **Visual design tasks need a vision-capable model.** The client must display MCP image content to the model. Text-only clients can use document and metadata tools, but cannot interpret the design screenshots.

---

### Prerequisites

- Python 3.10+
- FastMCP `>=3.0.2,<4` and Pillow `>=10.4.0` (installed by the commands below)
- Docker (optional, for containerized deployment)

### Installation

```bash
# Clone the repository
git clone https://github.com/dsphper/lanhu-mcp.git
cd lanhu-mcp

# Install the package and dependencies, including the CLI and bundle installer
python -m pip install -e .
python -m playwright install chromium

# Or use uv in your Python environment
uv pip install -e .
```

For an existing source checkout, upgrade dependencies with `python -m pip install -U -r requirements.txt` and reinstall the package with `python -m pip install -e .`. Restart the server and reconnect the MCP client so it discovers all 16 tools. Docker users should rebuild the image; restarting an old image does not load the new package or dependencies.

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

# Equivalent installed console command
lanhu-mcp --transport http --host 127.0.0.1 --port 8000

# For a client that starts its own stdio server
lanhu-mcp --transport stdio
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

1. **Conversational Access**: Ask the connected AI to search and manage messages
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

**2. AI Uses the Four-Stage Analysis Workflow**
- ✅ STAGE 1: Global text scan, build overall understanding
- ✅ STAGE 2: Grouped detailed analysis (based on selected mode)
- ✅ STAGE 3: Reverse validation, check for missing requirements
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

### Visual Inspection and Asset Installation

```
Use this design version to implement the page. Inspect its regions, select the
source assets by node ID, prefer SVG where available, and install the asset
bundle in this project's public directory.
```

The coding agent can execute this sequence:

1. Find the design with `lanhu_get_designs`, then call `lanhu_get_design_overview` to obtain a stable `snapshot_id`.
2. Call `lanhu_inspect_design_region` with source coordinates or node IDs. Use the clean image, numbered image, text runs and asset IDs together.
3. Call `lanhu_export_design_assets` with the chosen `asset_ids` and `format_preference="prefer_svg"`. Check the export status, source resolution and fallback fields.
4. Read the returned `bundle_resource` through MCP and install it **on the coding agent's machine**:

```bash
python -m lanhu_design.install \
  --mcp-url 'http://localhost:8000/mcp' \
  --resource-uri 'lanhu://design/SNAPSHOT_ID/bundle/BUNDLE_ID' \
  --output '/absolute/path/to/frontend/public'
```

The installer verifies the manifest and hashes, then writes `install-receipt.json` with the asset/node IDs and actual local paths. The model uses that mapping to bind resources in code. The server's cache path is not a client path, and the legacy `lanhu_get_design_slices` tool returns a list rather than installing files. See [DESIGN_CONTEXT.md](DESIGN_CONTEXT.md) for local ZIP installation, text/font fields, version rules and limits.

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
| `lanhu_list_product_documents` | Discover product documents in a project | Find a PRD/prototype before choosing its pages |
| `lanhu_get_pages` | Get prototype page list | Must call before analyzing requirements |
| `lanhu_get_ai_analyze_page_result` | Analyze prototype page content | Extract requirement details |
| `lanhu_get_designs` | Get UI design list | Must call before viewing designs |
| `lanhu_get_ai_analyze_design_result` | Analyze UI designs | View design drafts |
| `lanhu_get_design_slices` | Get legacy slice URLs and metadata | Inspect available resources without installing files |
| `lanhu_get_design_overview` | Pin a version and return a visual snapshot with stable node IDs | Start visual implementation from a specific design |
| `lanhu_inspect_design_region` | Inspect a region or nodes, clean/numbered crops, text runs and asset candidates | Connect visible elements to source specifications |
| `lanhu_export_design_assets` | Download and verify original/SVG/raster variants; return a portable bundle | Install selected assets on the coding agent's machine |
| `lanhu_say` | Post message | Team collaboration, @mentions |
| `lanhu_say_list` | View message list | Query message history |
| `lanhu_say_detail` | View message details | View full content |
| `lanhu_say_edit` | Edit message | Modify published messages |
| `lanhu_say_delete` | Delete message | Remove messages |
| `lanhu_get_members` | View collaborators | View team members |

The 16 tools include a server-local `lanhu_say*` message board; those messages are not Lanhu's native design review comments.

## 📁 Project Structure

```
lanhu-mcp-server/
├── lanhu_mcp_server.py          # Main server file
├── lanhu_design/                # Snapshots, regions, text, source variants and bundle installer
├── DESIGN_CONTEXT.md            # Visual tool and asset delivery contract
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Docker image
├── data/                         # Data storage directory
│   ├── messages/                 # Message data
│   ├── axure_extract_*/          # Axure resource cache
│   ├── lanhu_designs/            # Legacy design cache
│   └── design_context/           # Versioned visual snapshots and asset bundles
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
- ✨ **Tool-Assisted Execution**: The model can inspect, select and install assets; implementation choices and visual verification remain its responsibility

## 📊 Performance and Verification

- Screenshot latency depends on source size, browser startup, network and cache state; no universal timing or accuracy benchmark is claimed.
- Verified asset files can be reused; the installer skips identical local files and rejects conflicting content.
- Visual snapshots isolate versions and preserve image/node provenance. The new APIs do not change every legacy cache path.
- An anonymized exploration covered 57 Sketch-source designs and 12 representative workflow scenarios. Before the oversized-image fix, 11 scenarios completed; the previously failing large-image case now passes bounded-preview and native-region checks through an installed package. Real Figma and Photoshop imports are not yet covered by that sample set.
- Regression tests cover source identity, coordinates, versions, regional images, mixed text styles, variant selection and bundle installation. These are data/delivery checks, not a measured frontend reconstruction rate.

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

- [ ] Validate more real Figma and Photoshop imports; current cross-project samples are Sketch-source designs
- [ ] Add implementation screenshot/DOM comparison and font availability checks
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
- This project reads Lanhu APIs and asset CDNs and caches data on the configured MCP server. A remote deployment stores that cache on the server, not on each client.
- Optional Feishu notifications send message content to the configured webhook. Export bundles and images are transferred to requesting MCP clients.
- Keep the configured Lanhu Cookie, project cache and exported bundles private; the service uses one configured account rather than per-caller Lanhu authorization.
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

<!-- Last checked: 2026-09-09 08:36 -->
