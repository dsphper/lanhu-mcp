# Maintaining Lanhu MCP

Release working behavior with reproducible evidence. A screenshot, a successful
API response, a passing parser test, and a faithful generated frontend are
different results; report exactly which one was verified.

## Development and regression

Use Python 3.10 or newer in a virtual environment. CI exercises Python 3.10 and
3.13 with synthetic fixtures and mocked network responses; it requires no Lanhu
account or browser installation.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
export LANHU_COOKIE='test-placeholder-not-a-real-cookie'
export DDS_COOKIE='test-placeholder-not-a-real-cookie'
export DATA_DIR="$(mktemp -d)"
export FEISHU_WEBHOOK_URL=''
python -m pytest
python -m pip install build twine
python -m build
python -m twine check dist/*
```

The packaging job also installs the resulting wheel in a fresh virtual
environment, changes out of the repository, and checks `lanhu-mcp --help`,
`lanhu-mcp --version`, module imports, a real stdio MCP handshake/tool listing,
and synthetic ZIP installation/reuse through the client asset installer's CLI.
Both editable and wheel environments run `pip check` for dependency conflicts.
This catches missing package files that an editable install can hide. Default
`python -m build` builds both an sdist and a wheel from that sdist.

Branch CI also builds the production Dockerfile without pushing an image, then
checks the installed CLI and a headless Chromium render with networking disabled.
The draft-PR helper waits for this container check as well as Python and docs checks.

For data-contract changes, retain cases for exact-version selection, duplicate
names and IDs, source coordinates, hidden ancestors, rich text, missing DDS,
asset variants, corrupt downloads, partial exports, and bundle installation.
Test the bug's observable behavior instead of asserting internal implementation
details. Add synthetic reproductions of newly discovered source structures.

Document new/renamed tools in both [README.md](README.md) and
[README_EN.md](README_EN.md), and describe the design contract in
[DESIGN_CONTEXT.md](DESIGN_CONTEXT.md). The read-only documentation job compares
both tool tables with actual registrations and checks local file links. It does
not commit timestamps or generate artificial activity.

## Compatibility evidence and current limits

The September 2026 exploratory account study sampled 57 designs in 25 projects.
All discovered real source files were Sketch. It included duplicate layer names,
deep trees, long pages, rich text, `set`/`setChild`, and designs without explicit
exports. Of 12 representative designs exercised through context and asset
delivery, 11 completed and one 7680 × 16492 reference image exceeded the image
decode limit before the bounded-preview implementation. That large-image case
has since passed live overview and native-region checks through the installed
package. These are sample observations, not a platform-wide success rate.

Figma and Photoshop structures have synthetic regression tests; this does not
establish real-account compatibility for those formats. When extending support,
record source application/plugin versions, the structure exercised, and whether
it was checked against the native Lanhu interface. Keep privately collected
evidence private unless the owner explicitly licenses it for publication.

The visual APIs are not a completed frontend generator. The calling model must
interpret component boundaries, layout and semantics. Font names do not provide
font files or licenses. Source-resolution checks cannot create absent detail.
Browser rendering and CSS fidelity need separate end-to-end evaluation. Consult
the current [design contract](DESIGN_CONTEXT.md) for implemented behavior and
reported gaps; do not label a gap solved from a successful metadata parse alone.

Do not publish claims such as “95% accurate” or “100% faithful” without a defined
evaluation, baseline, sample selection, scoring method, and reproducible results.
Report counts and limitations separately for parsing, visual context, resource
delivery, and generated-page comparisons.

## Private account data

Never add real Cookies, tokens, user IDs, private project payloads, signed asset
URLs, screenshots, downloaded designs, or browser profiles to public fixtures,
issue reports, packages, or workflow artifacts. Use fictional IDs and generated
images in tests. Keep runtime downloads outside version control and review the
actual staged diff before publishing. `.gitignore` is a convenience, not a secret
scanner.

Run optional live checks locally with authorized account data and an isolated
`DATA_DIR`. Check the same explicit design/version in the native website, then
compare source coordinates, designer export counts, rich text, actual download
dimensions, and the client installation receipt. Publish only the aggregate
result and an anonymized synthetic reproduction. Do not configure account
Cookies as required CI secrets.

## Release procedure

1. Choose the version and update `lanhu_design.__version__` in
   `lanhu_design/__init__.py` and the changelog together. `pyproject.toml` derives
   the package version from that constant. Include behavior changes, migration
   notes, and remaining limitations.
2. Write `RELEASE_NOTES_vX.Y.Z.md`, or a `## [X.Y.Z]` section in
   [CHANGELOG.md](CHANGELOG.md). Release notes use that text, never an unfiltered
   dump of timestamp-only commits.
3. Run the tests and build locally. Review the PR, then confirm CI and
   documentation checks for the exact commit to be tagged. Changes involving
   images or source schemas also need the relevant visual/account regression.
4. Create and push the stable `vX.Y.Z` tag when ready to publish. The tag workflow
   verifies that it equals the package version and reruns the test/build gates.
   It publishes the `linux/amd64` and `linux/arm64` Docker image to GHCR only after
   those gates pass; GitHub Release creation and the tested wheel/sdist attachments
   follow successful image publication. Docker builds use QEMU for the second
   architecture; an untested local Dockerfile edit is not proof both builds work.
5. Inspect the workflow and published artifacts. Test the installed distribution
   and container before announcing availability. If a job fails, repair and
   rerun as appropriate; do not move an already published tag to different code.

The release workflow supports stable tags only. PyPI publishing is not enabled.
GitHub tests and documentation have `contents: read`; only the Docker job gains
`packages: write`, and only release creation gains `contents: write`. Branch
protection and required status checks are repository settings and must be enabled
by maintainers separately; committing workflows does not change those settings.

For the v1.8.0 update only, a successful push build of the upstream
`codex/visual-design-context` branch can open a **draft** PR against `main`, using
`RELEASE_NOTES_v1.8.0.md` as its body. It waits for the existing test/package and
documentation and non-publishing container jobs; it does not run them twice. The job uses the workflow's
`GITHUB_TOKEN` with `contents: read` and `pull-requests: write`, skips creation if
an open PR already exists, and does not run on pull-request events or forks.
If repository settings prohibit Actions from creating PRs, it reports a warning
without bypassing the restriction or changing the test gate results. It never
merges, pushes to `main`, or creates a release tag. This branch-specific helper
can be removed after the update; future contributions may open PRs manually.

## Triage

Prioritize wrong-version output, corrupted or misidentified assets, data exposure,
and reproducible installation failures ahead of new tool count. Ask bug reporters
for the package version, source application/version if known, the failing step,
and a sanitized reproduction. Do not ask for their Cookie in an issue. Separate
upstream authentication/API changes from parser, export, and model interpretation
issues so fixes can be verified at the appropriate layer.
