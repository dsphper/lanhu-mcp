# 更新日志 / Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `LOCAL-STDIO.md`: Docker-free local Python stdio guide (clone, install, verify, register with common MCP clients).

### Fixed
- Add `socksio` dependency so httpx can use SOCKS proxies from the environment.
- `run-stdio.sh` / `run-stdio.bat` support optional `LANHU_DISABLE_SYSTEM_PROXY=1` to clear inherited proxy variables and set `NO_PROXY=*` for direct connections during local stdio startup.

## [1.8.6] - 2026-09-24

### Added

- Added `lanhu_inspect_requirement_region`, which returns compact visual evidence around rendered text, a stable text-block ID, a long-page tile ID, or an explicit source-page rectangle.
- Repeated text now returns bounded candidate previews instead of silently selecting the first occurrence. The caller can choose a stable `Bxxxx` block ID and request tight, context, or section crops.

### Changed

- Long Axure detail tiles now preserve the complete content width and split only along the vertical axis. Default strips are at most 960 source pixels high with 96 pixels of overlap, keeping form rows and table columns together.
- Visible Axure text blocks include deterministic page-local IDs. No OCR or layer-name convention is required.

### Fixed

- Region and sparse-canvas captures use Chrome DevTools `captureBeyondViewport`, including pages whose useful content begins far from the canvas origin.
- The final long-page tile is balanced instead of being merged into an oversized tail.

### Compatibility

- Existing full screenshots, `text_only`, and requirement analysis calls remain available. Screenshot cache schema 4 rebuilds long-page tile metadata once after upgrade.
- The single-file server still embeds `lanhu_design`; replacing `lanhu_mcp_server.py` remains a supported upgrade for environments whose dependencies are already installed.

### Verified

- All 216 offline tests pass, and a fresh wheel install exposes all 17 tools through a real FastMCP stdio handshake.
- A six-document, nine-page structural audit covered 632 text anchors and 448 visual elements; a 1600×1100 context crop intersected nearby visible evidence for all 632 anchors.
- On the authorized 1920×4402 sample, `T002` is now a 1920×960 full-width strip and includes the ambiguous instruction plus both target fields in one image.
- The exact instruction query returned two focused images totaling about 208 KiB, compared with about 1.3 MiB for the full screenshot plus four tiles in the benchmark sample.

See [v1.8.6 release notes](RELEASE_NOTES_v1.8.6.md) for the workflow and validation details.

## [1.8.5] - 2026-09-24

### Added

- Long Axure pages now keep the established full screenshot and add overlapping source-resolution detail tiles with stable tile IDs, page coordinates, and text-block mappings.
- `lanhu_get_ai_analyze_page_result` accepts `tile_offset` and `tile_limit` so callers can page through large documents without returning every tile at once.

### Fixed

- Off-screen tiles use Chrome DevTools `captureBeyondViewport`, including a bounded scroll warm-up for lazy page content and bottom-edge clips that Playwright could reject after pixel rounding.
- Detail-tile failures degrade to the existing full screenshot instead of failing the requirement page.
- Image labels are interleaved with MCP image content, preventing page-to-image mapping errors when one page produces several images.
- Local Axure navigation tolerates a delayed `DOMContentLoaded` event after the target document and body are already usable.

### Compatibility

- Normal pages, `text_only`, and the main `screenshot_path` keep their previous behavior. Screenshot cache schema 3 rebuilds metadata once after upgrade.

### Verified

- All 211 offline tests pass.
- On an authorized live long page, the v1.8.4 and v1.8.5 main PNGs were both 1920×3683 and pixel-identical; v1.8.5 additionally returned four readable PNG tiles through FastMCP.
- In that sample, local cold rendering changed from 2.495 seconds to 2.934 seconds (+0.439 seconds), while the cached public MCP call returned five PNG contents in 0.752 seconds.
- A forced DevTools tile failure still returned a successful full-page PNG and explicit tile diagnostics.

See [v1.8.5 release notes](RELEASE_NOTES_v1.8.5.md) for the compatibility contract and validation details.

## [1.8.4] - 2026-09-24

### Fixed

- Requirement `text_only` analysis no longer scans design styles or captures full-page screenshots.
- `lanhu_mcp_server.py` now embeds the project-owned `lanhu_design` package, restoring full single-file deployment without a sidecar source directory; missing optional third-party design dependencies no longer crash requirement tools.
- Axure rendering uses bounded DOM/page readiness instead of waiting for `networkidle` plus a fixed two-second delay on every page.
- Axure text extraction now returns only rendered text blocks with source-page bounds; hidden/unrendered annotations are excluded from requirement prose.
- Very large sparse Axure canvases are cropped to visible content with the crop region reported to the caller.
- Figma imports with absolute nonzero artboard origins normalize mixed absolute/local layer coordinates while retaining original bounds; unverified sources are read-only and cannot export.
- Requirement analysis reuses the downloaded sitemap instead of requesting it twice.
- Matching versioned requirement caches can return without contacting Lanhu; cache metadata now persists the page list needed for the offline fast path.
- Relative `DATA_DIR` values resolve against the `.env` or source directory, so cache location no longer changes with the MCP client's working directory.
- POSIX and Windows installers route Playwright 1.58+ Chromium downloads through npmmirror's Chrome for Testing mirror, with legacy and official fallbacks.

### Verified

- A live three-page v1.8.3 cold render took 10.118 seconds; the corrected v1.8.4 internal full render took 2.565 seconds.
- Real MCP stdio warm calls completed in 0.135–0.136 seconds and returned the expected text and full-page PNG contents.
- Regression coverage enforces no-network exact-version cache hits, one sitemap request per analysis, screenshot-free text-only mode, hidden Axure text filtering, sparse-canvas cropping, Figma nonzero-origin mapping, and full embedded single-file startup.
- Windows release verification installs and launches Chromium before completing the MCP smoke test.

See [v1.8.4 release notes](RELEASE_NOTES_v1.8.4.md) for the failure analysis and validation evidence.

## [1.8.3] - 2026-09-20

### Added

- GitHub release verification now runs the Windows source installer on `windows-latest`.
- The Windows gate installs dependencies, downloads and launches Chromium, checks the installed CLI, and completes an MCP stdio handshake.

### Fixed

- `easy-install.bat` supports an explicit noninteractive audit mode without changing the normal user prompts.
- Windows Python version detection no longer uses `>` inside nested `cmd.exe` parsing, which previously misclassified Python 3.13 as unsupported.
- Windows installer failures no longer wait for interactive `pause` input in automation.

See [v1.8.3 release notes](RELEASE_NOTES_v1.8.3.md) for the Windows validation contract.

## [1.8.2] - 2026-09-20

### Fixed

- Source installers now prefer Aliyun PyPI and automatically fall back to Tsinghua and official PyPI when the default mirror rejects or cannot serve a current pip client.
- Explicit `PIP_INDEX_URL` overrides remain authoritative.
- POSIX and Windows installers change to their own checkout directory before touching relative paths.
- Added clean-install regression coverage for mirror ordering and checkout-relative execution.

See [v1.8.2 release notes](RELEASE_NOTES_v1.8.2.md) for the public-tag installation audit.

## [1.8.1] - 2026-09-20

### Fixed
- Source installers now reject Python versions below 3.10 before dependency resolution and install the project itself, including the `lanhu-mcp` console entry point.
- Installer subprocesses no longer fail when terminal clearing is unavailable, and stdio launchers report a direct installation instruction when the virtual environment is missing.
- Dependency downloads use longer timeouts and retries, without forcing an unrelated pip upgrade.

### Changed
- Installer scripts default to Tsinghua PyPI and the npmmirror Playwright browser mirror for the project's primarily Chinese user base; both remain overridable through environment variables.
- Chinese and English setup instructions now create an isolated virtual environment and match the actual launcher paths.
- Added regression coverage for installer syntax, Python 3.9 rejection, editable package installation, domestic mirror defaults, and missing stdio environments.

See [v1.8.1 release notes](RELEASE_NOTES_v1.8.1.md) for the clean-install validation performed before release.

## [1.8.0] - 2026-09-10

### Added
- Versioned visual design overviews and node/region queries with clean and numbered images.
- Original asset download, decoding/hash checks, SVG/raster selection, MCP resource bundles, and a client installer.
- UTF-16 text runs and explicit font dependencies; bounded large-image previews and native region requests.

### Fixed
- Sketch slice coordinates, stable source identity, hidden-parent handling, and explicit source/decoder gaps.
- Installed CLI configuration and entry point; notification diagnostics no longer write to stdio protocol output.
- Signed reference refresh, font inventory pagination, and downloaded variant validation.

### Changed
- Package version is maintained in one place; FastMCP/Pillow and runtime dependencies are aligned.
- Replace timestamp-only commits with documentation checks; add offline CI, package/stdio smoke checks, and gated releases.

See [v1.8.0 release notes](RELEASE_NOTES_v1.8.0.md) for upgrade steps and verified scope.

## Initial release feature summary

### 🎉 Initial Release Features

#### ✨ Added
- **需求文档分析**
  - 支持 Axure 原型自动提取和解析
  - 三种分析模式：开发视角、测试视角、快速探索
  - 四阶段工作流（全局扫描 → 分组分析 → 反向验证 → 生成交付物）
  - 智能缓存机制（基于文档版本号）
  - 页面截图和文本提取

- **UI 设计支持**
  - UI 设计图批量下载和展示
  - 切图自动识别和导出
  - 智能文件命名（基于图层路径）
  - 设计元数据提取（颜色、透明度、阴影等）

- **团队协作留言板**
  - 项目级和全局留言板
  - 五种消息类型（normal/task/question/urgent/knowledge）
  - @提醒功能（支持飞书机器人通知）
  - 协作者追踪
  - 消息搜索和筛选（支持正则表达式）
  - 消息编辑和删除
  - 10个标准元数据字段自动关联

- **性能优化**
  - 基于版本号的永久缓存
  - 增量资源更新
  - 并发下载和处理
  - 智能文件完整性检查

- **安全机制**
  - Task 类型消息的安全限制（只读查询）
  - Cookie 环境变量配置
  - 用户身份识别（从 URL 参数）
  - 角色归一化映射

#### 📖 Documentation
- 详细的中英文 README
- 贡献指南（CONTRIBUTING.md）
- MIT 开源许可证
- Docker 部署支持

#### 🛠️ Infrastructure
- FastMCP 框架集成
- Playwright 浏览器自动化
- HTTPx 异步 HTTP 客户端
- BeautifulSoup HTML 解析
- 飞书 Webhook 集成

---

## Future Roadmap

### v1.1.0 (计划中)
- [ ] 支持 Figma 设计平台
- [ ] 支持 Sketch 文件解析
- [ ] 增加 Web 管理界面
- [ ] 支持更多消息板功能（回复、点赞、标签）

### v1.2.0 (计划中)
- [ ] AI 辅助工时估算
- [ ] 技术栈智能推荐
- [ ] API 文档自动生成
- [ ] 前后端工作量分析

### v2.0.0 (计划中)
- [ ] 企业级权限管理
- [ ] 多租户支持
- [ ] 审计日志
- [ ] 性能监控和告警
- [ ] 国际化支持（更多语言）

---

## Version History

### [1.4.0] - 2026-03-26

#### Changed
- 文档与配置示例持续同步（README、元数据、格式整理）
- 更新 README 中微信群二维码图片（`images/wechat.jpg`）

### [1.1.0] - 2026-02-27

#### 设计图分析能力升级（Design Analysis）
- **设计图分析能力质的提升**
  - 分析设计图时可获取**详细设计参数**：组件尺寸、间距、颜色值、字体大小等精确数值，便于还原设计
  - **设计图转代码**：自动将蓝湖设计 Schema 转为 HTML+CSS，与蓝湖原生导出效果对齐，AI 可直接参考实现
  - 支持按**序号**（如 `6` 表示第 6 个）或**完整名称**（如 `6_friend页_挂件墙`）指定要分析的设计图
  - 返回结果中图片与代码一一对应，便于 AI 关联视觉与实现
- 新增依赖：htmlmin（HTML 压缩）

### [1.0.0] - 2025-12-17

#### 🎉 首次发布

首个开源版本，包含核心功能：
- ✅ Axure 原型分析
- ✅ UI 设计图查看
- ✅ 切图导出
- ✅ 团队留言板
- ✅ 飞书通知集成

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to contribute to this project.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

<!-- Last checked: 2026-09-11 02:59 -->
