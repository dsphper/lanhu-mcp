# v1.8.0 — Visual design context and verified asset delivery

AI clients can now locate a design element in an image, query its stable source ID,
and install the matching original assets in their own workspace. Duplicate layer
names no longer need to be treated as unique identifiers.

## Added

- `lanhu_get_design_overview`: exact-version snapshots, reference images, a
  paginated node index, and a full-design font dependency summary.
- `lanhu_inspect_design_region`: clean and numbered crops, source ancestors,
  coordinates/styles, asset IDs, UTF-16 text runs, and source/quality limitations.
- `lanhu_export_design_assets`: original-file download and decoding, pixel/hash
  verification, explicit asset categories, original/SVG/raster selection, and
  portable MCP resource bundles.
- `python -m lanhu_design.install`: read a bundle from MCP or a local ZIP, validate
  it, install assets on the client, and record source IDs and actual local paths.
- Large-reference handling: bounded overview images and source-coordinate region
  requests. Provider failures are reported as lower-resolution fallbacks rather
  than incorrectly claiming original detail.

## Fixed

- Legacy Sketch slice positions now read `left/top`, preserving fractional values
  and valid zeroes. Designer exports and rendering helpers are identified separately.
- Font requirements survive overview pagination and mixed numeric/named weights.
- Signed reference URLs refresh without changing immutable source identity.
- Downloaded formats are checked against variant requests; failures retain the
  selection metadata needed to retry the intended asset.
- MCP visual errors are ordinary JSON objects with meaningful decoder errors.
- Installed CLI configuration reads an explicit `LANHU_ENV_FILE`, a source-local
  `.env`, or the caller's `.env`; process environment variables remain authoritative.
- Notification diagnostics go to stderr so they cannot corrupt stdio JSON-RPC.
- The `lanhu-mcp` entry point now supports `--help`, `--version`, and transport/host/port
  options. The Docker image includes the design package and installs the actual wheel-compatible project.

## Maintenance

- Package version is derived from `lanhu_design.__version__`.
- Dependencies now require FastMCP `>=3.0.2,<4` and include Pillow, dotenv, and HTML minification.
- CI tests supported Python versions, builds wheel/sdist, checks dependencies,
  exercises installed entry points and stdio, and validates the documented tool inventory.
- Releases require verified packages, curated notes, and successful container builds.
- The scheduled timestamp-only commit workflow has been replaced with read-only
  documentation checks. There are no benchmark-free accuracy promises in this release.

## Upgrade

```bash
python -m pip install --upgrade -e .
lanhu-mcp --version
lanhu-mcp --transport stdio
```

Restart the MCP server/client connection to discover the three new tools. For an
HTTP service, use `lanhu-mcp --transport http --host 127.0.0.1 --port 8000`, adjusting
the bind address for the deployment environment.

The existing tools remain available. Their generated HTML is a reference, not a
guarantee of production-ready UI. New version guarantees apply to the new snapshot
workflow; this release does not redesign the legacy Axure analysis/cache workflow.

## Validation scope and limitations

Offline regression tests use synthetic fixtures. Private validation sampled 57
Sketch designs across different plugin versions and exercised representative
design, crop, resource, and client-install flows. Private source files, cookies,
project IDs, and screenshots are not included in the repository.

This release does not generate a complete frontend application, infer business
components in Python, bundle proprietary fonts, or guarantee responsive behavior
and pixel-identical output. Figma/Photoshop adapters have synthetic coverage;
real-source coverage is still being expanded. Nonzero canvas origins and complex
transform/constraint semantics remain explicitly qualified. See
[DESIGN_CONTEXT.md](DESIGN_CONTEXT.md) for the data contract and limits.
