# Lanhu MCP v1.8.7

This patch release improves local **stdio** startup when SOCKS or IDE-injected proxies interfere with httpx, and adds a Docker-free setup guide. Thanks to @liuhean2021 for the original contribution (supersedes community PR #130).

## SOCKS proxy support

- Declares `socksio>=1.0.0` in project dependencies so httpx can use `ALL_PROXY` / `socks5://` style environment proxies after `pip install -e .` or a fresh install.

## Optional direct connection (`LANHU_DISABLE_SYSTEM_PROXY`)

- When MCP client `env` sets `LANHU_DISABLE_SYSTEM_PROXY=1`, `run-stdio.sh` and `run-stdio.bat` clear inherited proxy variables (upper and lower case on Windows) and set `NO_PROXY=*` / `no_proxy=*` so httpx does not fall back to OS-level proxy settings.
- Default remains unchanged: proxies are respected unless you opt in.

## Documentation

- New [LOCAL-STDIO.md](LOCAL-STDIO.md): clone from `https://github.com/dsphper/lanhu-mcp.git`, install, verify, and register with common MCP clients (bash wrapper and optional direct script examples).
- [README.md](README.md): link, stdio env var notes, and FAQ entry.

## 中文摘要

- 新增 `socksio` 依赖，修复本地 stdio 在 SOCKS 代理环境下 httpx 无法工作的问题。
- 可选环境变量 `LANHU_DISABLE_SYSTEM_PROXY=1` 用于强制直连蓝湖（排障场景，默认不开启）。
- 新增 `LOCAL-STDIO.md` 纯本地按需启动指南。

## Validation

- Full offline test suite: **211 passed**, 5 skipped (Playwright Chromium not installed in the validation environment).
- `bash -n run-stdio.sh`; editable install confirms `socksio` importable.

## Upgrade

Pull `v1.8.7`, run `./venv/bin/python -m pip install -e .` (or reinstall) to pick up `socksio`, then restart your MCP client. Docker users should rebuild the image from the tag.
