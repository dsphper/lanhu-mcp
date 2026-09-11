"""Install a verified Lanhu asset bundle in the coding agent's local workspace.

The MCP server may run on another machine.  Its resource URI, rather than its
filesystem path, is the hand-off to this client.  Asset filenames come from the
manifest and are independent of human-assigned layer names.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import binascii
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile
from typing import Any
from urllib.parse import urlparse
import zipfile


MAX_BUNDLE_BYTES = 256 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 512 * 1024 * 1024
MAX_ASSET_BYTES = 128 * 1024 * 1024
MAX_MANIFEST_BYTES = 2 * 1024 * 1024
MAX_ZIP_ENTRIES = 4096
RECEIPT_NAME = "install-receipt.json"


class BundleInstallError(ValueError):
    """The bundle cannot be safely and completely installed."""


def _safe_zip_path(name: str, *, directory: bool = False) -> PurePosixPath:
    if not isinstance(name, str) or not name or "\\" in name or "\x00" in name:
        raise BundleInstallError(f"Unsafe ZIP path: {name!r}")
    raw = name[:-1] if directory and name.endswith("/") else name
    parts = raw.split("/")
    if any(part in ("", ".", "..") or ":" in part for part in parts):
        raise BundleInstallError(f"Unsafe ZIP path: {name!r}")
    path = PurePosixPath(raw)
    if path.is_absolute():
        raise BundleInstallError(f"Absolute ZIP path: {name!r}")
    return path


def _read_checked_bundle(bundle_bytes: bytes) -> tuple[dict[str, Any], list[tuple[dict[str, Any], bytes]]]:
    if not isinstance(bundle_bytes, bytes) or not bundle_bytes:
        raise BundleInstallError("Bundle must be non-empty bytes")
    if len(bundle_bytes) > MAX_BUNDLE_BYTES:
        raise BundleInstallError("Compressed bundle exceeds size limit")
    try:
        archive = zipfile.ZipFile(io.BytesIO(bundle_bytes))
    except (zipfile.BadZipFile, OSError) as exc:
        raise BundleInstallError("Bundle is not a readable ZIP archive") from exc

    with archive:
        infos = archive.infolist()
        if len(infos) > MAX_ZIP_ENTRIES:
            raise BundleInstallError("Too many ZIP entries")
        members: dict[str, zipfile.ZipInfo] = {}
        all_names: set[str] = set()
        total_size = 0
        for info in infos:
            safe_path = _safe_zip_path(info.filename, directory=info.is_dir())
            normalized_name = str(safe_path).casefold()
            if normalized_name in all_names:
                raise BundleInstallError(f"Duplicate ZIP path: {info.filename}")
            all_names.add(normalized_name)
            file_type = stat.S_IFMT(info.external_attr >> 16)
            if file_type not in (0, stat.S_IFREG, stat.S_IFDIR):
                raise BundleInstallError(f"ZIP links and special files are forbidden: {info.filename}")
            if (file_type == stat.S_IFDIR) != info.is_dir() and file_type != 0:
                raise BundleInstallError(f"Inconsistent ZIP entry type: {info.filename}")
            if info.flag_bits & 1:
                raise BundleInstallError("Encrypted ZIP entries are unsupported")
            total_size += info.file_size
            if info.file_size < 0 or total_size > MAX_UNCOMPRESSED_BYTES:
                raise BundleInstallError("Uncompressed bundle exceeds size limit")
            entry_limit = MAX_MANIFEST_BYTES if info.filename == "manifest.json" else MAX_ASSET_BYTES
            if info.file_size > entry_limit:
                raise BundleInstallError(f"ZIP entry exceeds size limit: {info.filename}")
            if not info.is_dir():
                members[info.filename] = info

        if "manifest.json" not in members:
            raise BundleInstallError("Bundle is missing root manifest.json")

        def read_member(name: str) -> bytes:
            try:
                with archive.open(members[name]) as source:
                    data = source.read(members[name].file_size + 1)
                if len(data) != members[name].file_size:
                    raise BundleInstallError(f"ZIP size mismatch: {name}")
                return data
            except (zipfile.BadZipFile, RuntimeError, OSError, EOFError) as exc:
                raise BundleInstallError(f"Cannot read ZIP entry: {name}") from exc

        try:
            manifest = json.loads(read_member("manifest.json"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise BundleInstallError("Invalid manifest JSON") from exc
        if not isinstance(manifest, dict):
            raise BundleInstallError("Manifest must be an object")
        if manifest.get("status") != "complete" or manifest.get("failed") != []:
            raise BundleInstallError("Only complete bundles with an empty failed list can be installed")
        assets = manifest.get("assets")
        if not isinstance(assets, list) or not assets:
            raise BundleInstallError("Manifest must contain a non-empty assets list")

        checked: list[tuple[dict[str, Any], bytes]] = []
        expected_names = {"manifest.json"}
        asset_ids: set[str] = set()
        for asset in assets:
            if not isinstance(asset, dict):
                raise BundleInstallError("Every manifest asset must be an object")
            asset_id = asset.get("asset_id")
            if not isinstance(asset_id, str) or not asset_id or asset_id in asset_ids:
                raise BundleInstallError("Every asset requires a unique non-empty string asset_id")
            asset_ids.add(asset_id)
            if "node_id" not in asset:
                raise BundleInstallError(f"Missing node_id for asset {asset_id}")
            relative_path = asset.get("relative_path")
            path = _safe_zip_path(relative_path)
            if len(path.parts) < 2 or path.parts[0] != "assets":
                raise BundleInstallError(f"Asset must be inside assets/: {relative_path}")
            if relative_path in expected_names:
                raise BundleInstallError(f"Duplicate manifest path: {relative_path}")
            expected_names.add(relative_path)
            if relative_path not in members:
                raise BundleInstallError(f"Missing asset file: {relative_path}")
            expected_hash = asset.get("sha256")
            if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
                raise BundleInstallError(f"Invalid SHA-256 for asset {asset_id}")
            expected_size = asset.get("bytes")
            if isinstance(expected_size, bool) or not isinstance(expected_size, int) or expected_size <= 0:
                raise BundleInstallError(f"Invalid byte count for asset {asset_id}")
            if expected_size != members[relative_path].file_size:
                raise BundleInstallError(f"Byte count mismatch: {relative_path}")
            data = read_member(relative_path)
            if hashlib.sha256(data).hexdigest() != expected_hash:
                raise BundleInstallError(f"SHA-256 mismatch: {relative_path}")
            checked.append((asset, data))
        unexpected_names = set(members) - expected_names
        if unexpected_names:
            raise BundleInstallError(f"Unlisted ZIP files: {', '.join(sorted(unexpected_names))}")
        return manifest, checked


def _check_local_path(path: Path) -> None:
    """Reject existing symlinks, including symlinked output directories."""
    for part in (path, *path.parents):
        if part.is_symlink():
            raise BundleInstallError(f"Local symlink is forbidden: {part}")
        if part != path and part.exists() and not part.is_dir():
            raise BundleInstallError(f"Local parent is not a directory: {part}")


def _existing_matches(path: Path, expected_hash: str) -> bool:
    _check_local_path(path)
    if not path.exists():
        return False
    if not path.is_file():
        raise BundleInstallError(f"Local asset path is not a regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    if digest.hexdigest() != expected_hash:
        raise BundleInstallError(f"Local asset conflict; refusing to overwrite: {path}")
    return True


def _temporary_file(parent: Path, data: bytes) -> Path:
    fd, name = tempfile.mkstemp(prefix=".lanhu-install-", dir=parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return temporary


def install_bundle(bundle_bytes: bytes, output_dir: Path) -> dict[str, Any]:
    """Validate the entire bundle and all local conflicts before writing assets.

    Identical existing assets are reused. Files are published atomically without
    overwriting another file. The managed install-receipt.json is atomically
    refreshed only after all assets are available, and includes absolute paths.
    """
    manifest, checked = _read_checked_bundle(bundle_bytes)
    # The caller chooses this root; canonicalize aliases such as macOS /var
    # and /tmp here. Symlinks inside that chosen root remain forbidden below.
    destination = Path(output_dir).expanduser().resolve()
    _check_local_path(destination)
    if destination.exists() and not destination.is_dir():
        raise BundleInstallError(f"Output is not a directory: {destination}")
    receipt_path = destination / RECEIPT_NAME
    _check_local_path(receipt_path)
    if receipt_path.exists() and not receipt_path.is_file():
        raise BundleInstallError(f"Receipt path is not a regular file: {receipt_path}")
    for asset, _ in checked:
        _existing_matches(destination / asset["relative_path"], asset["sha256"])

    receipt: dict[str, Any] = {
        "status": "complete",
        "installed": [],
        "skipped": [],
        "assets": [],
        "receipt_path": str(receipt_path),
    }
    for key in ("bundle_id", "snapshot_id", "design_id", "resolved_version", "version_id", "image_id", "project_id"):
        if key in manifest:
            receipt[key] = manifest[key]

    created: list[tuple[Path, int, int]] = []
    try:
        destination.mkdir(parents=True, exist_ok=True)
        for asset, data in checked:
            target = destination / asset["relative_path"]
            if _existing_matches(target, asset["sha256"]):
                receipt["skipped"].append(asset["asset_id"])
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                _check_local_path(target)
                temporary = _temporary_file(target.parent, data)
                try:
                    try:
                        # A hard link publishes the complete file but cannot
                        # overwrite a file created since the preflight check.
                        os.link(temporary, target)
                    except FileExistsError:
                        _existing_matches(target, asset["sha256"])
                        receipt["skipped"].append(asset["asset_id"])
                    else:
                        info = target.stat()
                        created.append((target, info.st_dev, info.st_ino))
                        receipt["installed"].append(asset["asset_id"])
                finally:
                    temporary.unlink(missing_ok=True)
            receipt["assets"].append({**asset, "local_path": str(target)})

        receipt_data = json.dumps(receipt, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
        temporary = _temporary_file(destination, receipt_data)
        try:
            _check_local_path(receipt_path)
            os.replace(temporary, receipt_path)
        finally:
            temporary.unlink(missing_ok=True)
    except BaseException:
        # Roll back only files created by this invocation, never reused files.
        for target, device, inode in reversed(created):
            try:
                info = target.lstat()
                if info.st_dev == device and info.st_ino == inode:
                    target.unlink()
            except OSError:
                pass
        raise
    return receipt


def _decode_resource_contents(contents: Any) -> bytes:
    from mcp.types import BlobResourceContents

    if not isinstance(contents, list) or len(contents) != 1 or not isinstance(contents[0], BlobResourceContents):
        raise BundleInstallError("Expected exactly one MCP binary resource; text/error resources cannot be installed")
    blob = contents[0].blob
    if len(blob) > ((MAX_BUNDLE_BYTES + 2) // 3) * 4:
        raise BundleInstallError("MCP bundle exceeds size limit")
    try:
        return base64.b64decode(blob, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise BundleInstallError("MCP binary resource contains invalid base64") from exc


async def _read_remote_bundle(mcp_url: str, resource_uri: str) -> bytes:
    from fastmcp import Client

    url = urlparse(mcp_url)
    if url.scheme not in ("http", "https") or not url.netloc or url.username or url.password:
        raise BundleInstallError("--mcp-url must be an HTTP(S) MCP endpoint without embedded credentials")
    token = os.environ.get("LANHU_MCP_AUTH_TOKEN") or None
    async with Client(mcp_url, auth=token, timeout=60) as client:
        contents = await client.read_resource(resource_uri)
    return _decode_resource_contents(contents)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--bundle", type=Path, help="Local ZIP bundle file")
    source.add_argument("--mcp-url", help="HTTP(S) endpoint of the remote Lanhu MCP server")
    parser.add_argument("--resource-uri", help="Bundle resource URI returned by the MCP export tool")
    parser.add_argument("--output", required=True, type=Path, help="Local workspace directory")
    args = parser.parse_args(argv)
    if args.mcp_url and not args.resource_uri:
        parser.error("--resource-uri is required with --mcp-url")
    if args.bundle and args.resource_uri:
        parser.error("--resource-uri can only be used with --mcp-url")
    try:
        if args.bundle:
            with args.bundle.open("rb") as source_file:
                bundle = source_file.read(MAX_BUNDLE_BYTES + 1)
        else:
            bundle = asyncio.run(_read_remote_bundle(args.mcp_url, args.resource_uri))
        receipt = install_bundle(bundle, args.output)
    except Exception as exc:
        print(f"Lanhu bundle installation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
