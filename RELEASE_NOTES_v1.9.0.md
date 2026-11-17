# Lanhu MCP v1.9.0

HTTP 服务现在可以按请求隔离蓝湖身份：多个用户共用同一进程时，各自携带自己的 Cookie，不再串号、也不再共享私有文档缓存。Thanks to @geniyangge (#139, closes #100).

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
- 服务端若仍配置 `LANHU_COOKIE`，没带头的请求会继续使用这个共享账号。
- 中文署名继续用 URL query，不要放进请求头。

## Validation

- Isolation unit tests plus a real FastMCP HTTP client check: header cookie reaches the tool, missing header falls back to env, concurrent Alice/Bob cookies do not mix.
- Full offline test suite passed in the release environment (Playwright Chromium tests skipped when the browser is absent).

## Upgrade

Pull `v1.9.0` (or download the GitHub Release), reinstall if you use a package install, and restart the MCP client. Add `X-Lanhu-Cookie` on each HTTP client if you want per-user identity.
