# Lanhu MCP v1.9.1

Same feature as v1.9.0: HTTP servers can isolate Lanhu identity **per request**. Download this tag, not v1.9.0 — the earlier tag passed tests but GitHub Release was blocked by Docker image publish.

Thanks to @geniyangge (#139, closes #100).

## Multi-tenant HTTP credentials

- Each HTTP request may send `X-Lanhu-Cookie` (and optionally `X-Lanhu-Dds-Cookie`).
- Header wins over the process `LANHU_COOKIE` / `DDS_COOKIE` environment variables.
- Download cache, metadata cache, and design-context instances are namespaced by a cookie hash (`data/ns-<hash>/…`).
- If a request carries a custom identity, DDS no longer falls back to the server-wide shared account.

stdio and existing single-account HTTP deployments are unchanged: they still use `LANHU_COOKIE`.

## Client config

Cookie goes in **request headers**, not the URL:

```json
{
  "mcpServers": {
    "lanhu": {
      "url": "http://HOST:8000/mcp",
      "headers": {
        "X-Lanhu-Cookie": "<your_lanhu_cookie>"
      }
    }
  }
}
```

For true isolation, do not set a shared `LANHU_COOKIE` on the server. Requests without the header still fall back to that shared account.

Chinese display names for the message board should stay on the URL (`/mcp?name=张三&role=后端`). HTTP headers must be ASCII; `X-Lanhu-Name` cannot carry raw Chinese.

## 中文摘要

- HTTP 多账号：请求头 `X-Lanhu-Cookie` 携带自己的蓝湖身份，缓存和设计上下文按账号隔离。
- 请下载 **v1.9.1**：[Releases](https://github.com/dsphper/lanhu-mcp/releases/latest)
- 服务端若仍配置 `LANHU_COOKIE`，没带头的请求会继续使用这个共享账号。
- 中文署名继续用 URL query，不要放进请求头。

## Validation

- Isolation unit tests plus a real FastMCP HTTP client check: header cookie reaches the tool, missing header falls back to env, concurrent Alice/Bob cookies do not mix.
- Offline test suite and Windows installer smoke passed in GitHub Actions for v1.9.0; this patch unblocks publishing.

## Upgrade

Download [v1.9.1](https://github.com/dsphper/lanhu-mcp/releases/tag/v1.9.1), reinstall if you use a package install, and restart the MCP client. Add `X-Lanhu-Cookie` on each HTTP client if you want per-user identity.
