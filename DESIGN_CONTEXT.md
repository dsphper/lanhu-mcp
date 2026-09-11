# Visual design context and original asset delivery

Available in **1.8.0**. Install or upgrade the package, restart the server and
reconnect the MCP client to load the three visual tools.

The visual tools let a multimodal coding agent connect what it sees to stable
source IDs. Python extracts source facts, draws numbered crops, and transfers
verified files. The calling model decides component semantics and implementation.
Layer names can be duplicated or meaningless.

## Workflow

1. Use `lanhu_get_designs` to find a design ID.
2. Call `lanhu_get_design_overview(url, design_id, version_id)` for a versioned
   snapshot, reference image, source canvas dimensions, and paginated node index.
3. Call `lanhu_inspect_design_region(snapshot_id, region=...)` or supply `node_ids`.
   Read the clear crop, stable `N` labels, source ancestors, text/styles, and asset
   IDs together. Follow `next_offset` when `truncated` is true.
4. Have the model select the appropriate assets by visual evidence and stable IDs.
   Call `lanhu_export_design_assets(snapshot_id, asset_ids=[...],
   format_preference="original")` to download selected source variants, verify
   actual dimensions and hashes, and prepare a ZIP.
5. Install the ZIP on the **coding agent's machine**, then use its receipt's
   `asset_id → node_id → relative_path/local_path` mapping when writing the page.

These are three new tools, in addition to the existing design listing tools.
The legacy full-HTML and slice-list tools remain available. Their output is a
reference, and the slice-list tool itself still does not install assets.

## Identity and version rules

- Use `design_id` from the project list; a human-readable name is not an ID.
- `version_id` chooses the exact source version. If omitted, use the URL's
  `versionId`, then the design's current version if the URL has none.
- Pass the explicit string `latest` to override a URL version.
- A prototype URL requires an explicit UI `design_id`. A mixed URL retaining an
  Axure `docId` will not overwrite its UI `image_id`. A stale or unrelated
  `versionId` fails clearly unless the caller explicitly chooses another version.
- Every subsequent query/export uses the immutable `snapshot_id`. Raw nodes,
  reference image, and optional DDS data belong to the selected design version.
- DDS failure is reported in capabilities/gaps; it does not silently substitute
  a layout from another version.
- Cached snapshots are separated by configured credentials. This remains a
  **single configured-account service**, not per-caller project authorization.

## Coordinates and visual queries

Example region query (coordinates are in the returned `source_canvas` space):

```json
{
  "snapshot_id": "the-returned-snapshot-id",
  "region": {"x": 400, "y": 650, "width": 1100, "height": 750},
  "limit": 30,
  "annotate": true
}
```

`source_region`, `image_size`, and `scale` describe the mapping between a source
region and its returned image. A high-resolution reference image may have twice
the source canvas dimensions; this does not change the source node coordinates.
Number labels are based on the node's source order within its snapshot and map
back to `node_id`. They are not names or semantic roles. Whole-image overview
annotation is off by default to avoid covering the design; enable it as needed.
Annotated queries return two images: the clean crop first, then the numbered
overlay. `image_order` identifies them, so labels never hide the only visual
evidence available to the model. Each version is also available as an MCP resource.

Source parents come from `parentID`/nested children. Geometric intersection is
only a query filter. Returned `ancestors` do not imply that everything inside a
rectangle is a child. Missing, cyclic, or ambiguous source relations are reported.
Zero-area lines and missing bounds remain source evidence; they do not prevent a
crop of valid nodes. Hidden nodes are omitted by default and can be queried with
`include_hidden`; a reference screenshot cannot reveal hidden states.

Raw attributes and DDS layout suggestions are separate. Complex transforms are
preserved with limitations in `gaps`, rather than approximated as exact CSS.
Nonzero source canvas origins currently fail with `UnsupportedCoordinates`;
their relationship to the reference image needs source-specific verification.
Visibility inherited from a hidden source ancestor is preserved separately as
`effective_source_visible`, and these nodes are not drawn over the visible image.
Logical/CSS unit conversion is not guessed from export density. Known source
families are flat Sketch `info[]`, nested Figma `artboard.layers`, and Photoshop
`board.layers`/asset metadata; individual source capabilities vary.

### Oversized reference images

When the original reference exceeds the local 80-million-pixel decode limit,
the snapshot uses an OSS preview with a long edge bounded to 4096 pixels. The
original dimensions remain in `original_reference_size`; `reference_size` is
the stored preview size. `visual_source="bounded_preview"` and the
`bounded_reference_preview` gap make that reduced detail explicit. This limits
decoded image memory; the original file still has to fit the download byte limit.

`lanhu_inspect_design_region` uses the asynchronous inspection path. It maps the
requested source-canvas region to original image pixels and asks OSS to crop
the original before resizing the crop for delivery. A successful response has
`visual_source="original_region"`. This preserves regional detail without
decoding the entire oversized image locally; the delivered crop still has an
output-size bound and is not an unbounded original-resolution export.

If the provider rejects the request or returns inconsistent dimensions,
inspection returns the bounded-preview crop with `native_region_unavailable`.
Requests beyond the regional processing limit report `region_provider_limit`;
choose a smaller region. Failure to obtain a valid bounded preview fails
snapshot preparation explicitly. Ordinary references use
`visual_source="original_reference"`.

The image provider operations follow Alibaba Cloud's official
[custom crop](https://www.alibabacloud.com/help/en/oss/user-guide/custom-crop)
and [resize](https://www.alibabacloud.com/help/en/oss/user-guide/resize-images-4)
parameters. Provider support and limits still apply; this is not a promise that
every Lanhu source URL accepts image processing.

### Text runs and font requirements

Region nodes include `text_spec` when source styles are included. Each entry in
`text_spec.text_runs` retains its source order, `source_pointer` and `raw_style`,
and exposes typed `start`, `length`, `text`, `font_family`, `font_size`,
`font_weight`, `color`, `line_height` and spacing fields where provided.
`offset_unit="utf16"` means locations and lengths count UTF-16 code units.
An emoji outside the BMP occupies two units; ranges are mapped to complete
Unicode characters rather than sliced using Python character offsets.

Duplicate, overlapping, out-of-bounds and split-surrogate ranges are preserved
and reported in `text_spec.gaps`. Invalid ranges have `text=null`; they are not
silently clipped or given the source's separate `content` value as a substitute.
Missing properties remain unknown. Font weights are not inferred from names
such as `ExampleSans-Semibold`. The base font style remains separate from runs.

Overview and region responses also list `font_requirements`. Each requirement
uses the source font name with `source="design"` and
`availability="not_checked"`, plus explicit weights, node counts and sample
node IDs. The per-node `text_spec.font_requirements` retains source pointers.
A source name may identify a PostScript face rather than an installed
CSS family. This release does not download font files, resolve font licenses or
check that the frontend machine has the required fonts.

## Original assets and quality

Without explicit IDs, export defaults to `kind="exported_asset"`.
`render_fallback`, `image_fill`, and `all` are explicit alternatives. A node can
have both a designer export and a DDS rendering; these have different asset IDs.
Their counts should not be added and called "designer-exported slices".

Files are identified by stable asset IDs and named using their hashes. No role
such as "claim button" is inferred from the source name. Asset candidates expose
`variants` with stable `variant_id`, `source_field`, `format_hint`, `is_original`
and `format_verification="requires_download"`; source URLs are omitted.

Choose one `format_preference` when exporting:

| Value | Selection behavior |
| --- | --- |
| `original` (default) | Preserve the normalized source's default file; this is not a claim that it has the highest resolution among every variant |
| `prefer_svg` | Choose a supplied SVG; if absent, use the original and record `selection_fallback="svg_unavailable_using_original"` |
| `raster` | Select an existing non-SVG candidate, including a source with an unknown format until download; fail when no candidate exists rather than rasterizing an SVG |

The downloader verifies actual file format after selection. A format hint does
not prove the downloaded bytes match it. Non-default variants have a distinct
delivery `asset_id` and preserve `base_asset_id`, so PNG and SVG versions can be
installed together without a filename collision. The manifest records
`requested_preference`, `selected_variant_id`, `selected_format_hint`,
`selected_source_field` and `selection_fallback` alongside the actual format.

The source asset file is not resized or synthetically sharpened. `target_dpr` checks
the decoded pixels against the source render bounds. A smaller source is marked
`resolution_limited`; upscaling does not count as higher source quality. Density
is relative to source bounds, so the coding agent must also consider its actual
CSS render size. SVGs are reported as vectors without inventing pixel dimensions.

The export manifest records actual MIME/format, dimensions, transparency bounds,
hash, bytes, asset/node IDs, local relative filenames, and resolution limitations.
Missing, corrupt, or HTML error responses produce `partial`/`failed`, not success.
Verified cache entries can be reused; modified cache files are downloaded again.
Credentials are sent only to the corresponding Lanhu API origin, not to asset
CDNs, including after redirects. Current source download limits are 64 MiB per
file and a fixed set of observed official Lanhu origins; unsupported hosts fail
explicitly and can be added after verification.

## Install on the client

The server and installer use FastMCP `>=3.0.2,<4`; image verification uses Pillow
`>=10.4.0`. Install the package with `python -m pip install -e .` from a checkout
on each machine that needs the CLI. Existing source deployments can refresh
dependencies with `python -m pip install -U -r requirements.txt`.
Rebuild Docker images after upgrading;
they must include the `lanhu_design` package as well as the server entry point.

The server returns `bundle_resource`, not an assumed path on the client.
From the coding agent's local environment (with this package installed):

```bash
python -m lanhu_design.install \
  --mcp-url 'http://localhost:8000/mcp' \
  --resource-uri 'lanhu://design/SNAPSHOT_ID/bundle/BUNDLE_ID' \
  --output '/absolute/path/to/frontend/public'
```

The installer uses MCP `read_resource` to transfer the ZIP, verifies its manifest
and all hashes, and writes local files plus `install-receipt.json`. If the endpoint
uses a bearer token, provide `LANHU_MCP_AUTH_TOKEN` in the local environment.
Authentication beyond a configured bearer token is not handled by this CLI.

For a previously transferred local ZIP:

```bash
python -m lanhu_design.install --bundle '/path/bundle.zip' --output '/path/frontend/public'
```

The destination root is chosen by the client. Existing identical files are
skipped; conflicting files are rejected. Partial packages, missing files,
incorrect hashes, unsafe ZIP paths and links are rejected. The receipt retains
the design/version provenance and actual installed paths. Raw resource URLs and
Lanhu cookies are not included in the frontend asset manifest.

For example, assets installed below a Vite `public` directory can be referenced
as `/assets/<filename>.png`; assets installed elsewhere should be imported using
that framework's normal convention. The model performs that source-code binding
from the receipt. This release does not rewrite an arbitrary React/Vue project.

## Scope and verification

Implemented: source adapters, exact-version snapshots, visual overview/region
queries, node IDs independent of names, original resource downloads and decoding,
portable MCP resources, client installation, and explicit failure results.

Not implemented in 1.8.0: automatic business-component classification,
responsive constraints absent from the source, arbitrary framework code generation,
prototype state-machine extraction, or a final implementation screenshot/DOM
comparison tool. The model must decide whether a merged image replaces child
elements; the service preserves the children and flags unknown coverage instead
of suppressing them based on a rectangle or name.

Synthetic regression tests cover renamed/duplicate layers, source variants,
coordinates and parents, historical versions, old/new snapshot separation,
region pagination, image decode failures, original pixel density, cache corruption,
ZIP installation, UTF-16 mixed-style text, missing typography, source variant
selection, oversized preview/region fallback and the MCP image/resource-to-client
flow. These checks validate source evidence and delivery, not final page fidelity.

Anonymized exploration covered 57 Sketch-source designs and 12 representative
workflow scenarios, including duplicate names, deep groups, long pages, mixed
text styles and designs with no marked exports. Before this release's oversized
image fix, 11 of the 12 workflows completed. The previously failing large-image case now passes live checks through an installed
package: a bounded overview and source-coordinate detail crop, without decoding the
full oversized raster locally. The same samples contain 2,348 text nodes and 2,393
style runs, whose ranges match their source text; this does not verify installed
fonts or browser typography. Real Figma and Photoshop import coverage remains
unverified. Private source fixtures, design names, project IDs and URLs are not
included in the repository.
