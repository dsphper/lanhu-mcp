Start the Lanhu MCP server.

Prerequisites:
- `LANHU_COOKIE` environment variable must be set
- Dependencies installed (`pip install -r requirements.txt`)
- Playwright browser installed (`playwright install chromium`)

```bash
python lanhu_mcp_server.py
```

The server will start at `http://localhost:8000/mcp`
