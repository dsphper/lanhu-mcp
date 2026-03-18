# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Lanhu MCP Server is a Model Context Protocol (MCP) server that integrates Lanhu (蓝湖) design collaboration platform with AI-powered IDEs (Cursor, Windsurf, Claude Code, etc.). It enables AI assistants to read requirement documents (Axure prototypes), UI designs, and manage team collaboration messages.

## Development Commands

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browser (required for screenshots)
playwright install chromium
```

### Running
```bash
# Run the MCP server (requires LANHU_COOKIE env var)
python lanhu_mcp_server.py

# Or with Docker
docker-compose up -d
```

### Testing
```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=term-missing

# Run specific test file
python -m pytest tests/test_basic.py -v
```

### Code Quality
```bash
# Format code
black lanhu_mcp_server.py

# Sort imports
isort lanhu_mcp_server.py

# Lint
flake8 lanhu_mcp_server.py
```

## Architecture

### Single-File Design
The entire MCP server is implemented in `lanhu_mcp_server.py` (~3800+ lines). This is intentional for simplicity and ease of deployment.

### Core Components

1. **FastMCP Framework**: Uses `fastmcp` to create MCP tools that AI assistants can call
2. **Playwright Integration**: Browser automation for rendering Axure prototypes and taking screenshots
3. **HTTP Client**: Uses `httpx` to communicate with Lanhu APIs
4. **Local Cache**: File-based caching in `data/` directory with version-based invalidation

### MCP Tools Exposed

| Tool | Purpose |
|------|---------|
| `lanhu_resolve_invite_link` | Parse share links |
| `lanhu_get_pages` | Get Axure prototype page list |
| `lanhu_get_ai_analyze_page_result` | Analyze prototype content |
| `lanhu_get_designs` | Get UI design list |
| `lanhu_get_ai_analyze_design_result` | Analyze UI design with parameters + HTML/CSS |
| `lanhu_get_design_slices` | Get slice/image assets |
| `lanhu_say` | Post team message |
| `lanhu_say_list` | Query messages |
| `lanhu_get_members` | Get collaborators |

### Data Flow

```
AI Client (MCP) → FastMCP Tool → Check Cache → Lanhu API → Process → Cache → Return
```

## Configuration

### Required Environment Variables

- `LANHU_COOKIE`: Authentication cookie from Lanhu web app (obtain from browser DevTools)

### Optional Environment Variables

- `SERVER_HOST`: Server host (default: `0.0.0.0`)
- `SERVER_PORT`: Server port (default: `8000`)
- `FEISHU_WEBHOOK_URL`: Feishu bot webhook for notifications
- `DATA_DIR`: Data storage directory (default: `./data`)
- `HTTP_TIMEOUT`: HTTP timeout in seconds (default: `30`)
- `VIEWPORT_WIDTH/HEIGHT`: Browser viewport dimensions
- `DEBUG`: Enable debug mode (`true`/`false`)

## Key Implementation Details

### Design JSON to HTML/CSS Conversion
The server includes a design schema converter (`_generate_html`, `_generate_css`) that transforms Lanhu's JSON design format into HTML + CSS, matching Lanhu's native export.

### CSS Utilities
- `_camel_to_kebab`: Convert camelCase to kebab-case
- `_format_css_value`: Auto-add `px` units to numeric values
- `_merge_padding`/`_merge_margin`: Combine individual properties into shorthand

### Caching Strategy
- Metadata cache: In-memory dict with version-based invalidation
- Resource cache: File-based in `data/axure_extract_*/` and `data/lanhu_designs/`
- Cache key: Combines URL identifiers with version ID

### Team Message Board
Messages are stored as JSON files in `data/messages/{project_id}.json`. Supports:
- Message types: `normal`, `task`, `question`, `urgent`, `knowledge`
- @mentions with Feishu notification integration
- Regex search and type filtering

## Python Version

Requires Python 3.10+ (uses modern type hints with `|` union syntax and `Annotated`).

## MCP Client Configuration

When connecting from AI clients, use URL parameters for user identity:
```
http://localhost:8000/mcp?role=Developer&name=YourName
```
