"""A downloaded bundle must be trustworthy before touching the user's project."""

import base64
import hashlib
import io
import json
from pathlib import Path
import stat
import sys
import tempfile
import zipfile

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from lanhu_design.install import BundleInstallError, _decode_resource_contents, install_bundle, main


def _asset(asset_id="stable-01", filename="assets/stable-01.png", data=b"original-pixels"):
    return {
        "asset_id": asset_id,
        "node_id": "layer-001",
        "name": "编组123",
        "relative_path": filename,
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "actual_pixel_size": {"width": 800, "height": 400},
    }


def _bundle(assets=None, files=None, status="complete", failed=None, extra=None):
    assets = [_asset()] if assets is None else assets
    files = {"assets/stable-01.png": b"original-pixels"} if files is None else files
    manifest = {
        "status": status, "assets": assets, "failed": [] if failed is None else failed,
        "bundle_id": "b-123", "design_id": "design-123", "resolved_version": "version-123",
    }
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        for path, data in files.items():
            archive.writestr(path, data)
        if extra:
            archive.writestr(*extra)
    return output.getvalue()


def test_install_then_reuse_same_content_and_write_absolute_receipt(tmp_path):
    output = tmp_path / "frontend"
    receipt = install_bundle(_bundle(), output)
    expected_path = output / "assets/stable-01.png"
    assert expected_path.read_bytes() == b"original-pixels"
    assert receipt["status"] == "complete"
    assert receipt["installed"] == ["stable-01"]
    assert receipt["skipped"] == []
    assert receipt["assets"][0]["local_path"] == str(expected_path)
    assert receipt["assets"][0]["node_id"] == "layer-001"
    assert receipt["assets"][0]["actual_pixel_size"] == {"width": 800, "height": 400}
    assert receipt["design_id"] == "design-123"
    assert receipt["resolved_version"] == "version-123"
    before = expected_path.stat().st_mtime_ns
    second = install_bundle(_bundle(), output)
    assert second["installed"] == []
    assert second["skipped"] == ["stable-01"]
    assert expected_path.stat().st_mtime_ns == before
    assert json.loads((output / "install-receipt.json").read_text()) == second


def test_same_layer_names_use_distinct_stable_files(tmp_path):
    assets = [_asset("a", "assets/a.png", b"one"), _asset("b", "assets/b.png", b"two")]
    receipt = install_bundle(_bundle(assets, {"assets/a.png": b"one", "assets/b.png": b"two"}), tmp_path)
    assert [item["name"] for item in receipt["assets"]] == ["编组123", "编组123"]
    assert (tmp_path / "assets/a.png").read_bytes() == b"one"
    assert (tmp_path / "assets/b.png").read_bytes() == b"two"


def test_later_local_conflict_prevents_all_writes(tmp_path):
    (tmp_path / "assets").mkdir()
    conflict = tmp_path / "assets/b.png"
    conflict.write_bytes(b"user changes")
    assets = [_asset("a", "assets/a.png", b"one"), _asset("b", "assets/b.png", b"two")]
    with pytest.raises(BundleInstallError, match="conflict"):
        install_bundle(_bundle(assets, {"assets/a.png": b"one", "assets/b.png": b"two"}), tmp_path)
    assert not (tmp_path / "assets/a.png").exists()
    assert conflict.read_bytes() == b"user changes"
    assert not (tmp_path / "install-receipt.json").exists()


@pytest.mark.parametrize("filename", ["../escape.png", "/tmp/escape.png", "assets/../escape.png", "assets\\escape.png", "C:/escape.png", "assets//a.png"])
def test_rejects_unsafe_paths_even_for_unlisted_files(tmp_path, filename):
    output = tmp_path / "frontend"
    with pytest.raises(BundleInstallError, match="path"):
        install_bundle(_bundle(extra=(filename, b"bad")), output)
    assert not output.exists()


def test_rejects_zip_symlink(tmp_path):
    link = zipfile.ZipInfo("assets/link.png")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with pytest.raises(BundleInstallError, match="links"):
        install_bundle(_bundle(extra=(link, b"../../elsewhere")), tmp_path / "frontend")
    assert not (tmp_path / "frontend").exists()


def test_rejects_local_symlink_parent_without_writing_outside(tmp_path):
    output, outside = tmp_path / "frontend", tmp_path / "outside"
    output.mkdir()
    outside.mkdir()
    (output / "assets").symlink_to(outside, target_is_directory=True)
    with pytest.raises(BundleInstallError, match="symlink"):
        install_bundle(_bundle(), output)
    assert list(outside.iterdir()) == []


def test_canonicalizes_caller_selected_output_alias_and_receipt_paths(tmp_path):
    actual = tmp_path / "actual"
    actual.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(actual, target_is_directory=True)
    receipt = install_bundle(_bundle(), alias / "frontend")
    assert receipt["assets"][0]["local_path"] == str(actual / "frontend/assets/stable-01.png")
    assert receipt["receipt_path"] == str(actual / "frontend/install-receipt.json")
    assert (actual / "frontend/assets/stable-01.png").read_bytes() == b"original-pixels"


def test_accepts_system_temporary_directory_aliases():
    # On macOS tempfile yields /var/folders/... while /var points to /private/var.
    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary) / "frontend"
        receipt = install_bundle(_bundle(), output)
        assert receipt["status"] == "complete"
        assert receipt["assets"][0]["local_path"] == str(output.resolve() / "assets/stable-01.png")


@pytest.mark.parametrize("status,failed", [("partial", []), ("failed", []), ("complete", [{"asset_id": "failed-one"}])])
def test_refuses_partial_or_failed_bundles(tmp_path, status, failed):
    output = tmp_path / "frontend"
    with pytest.raises(BundleInstallError, match="complete"):
        install_bundle(_bundle(status=status, failed=failed), output)
    assert not output.exists()


@pytest.mark.parametrize("kind", ["hash", "size", "missing"])
def test_validates_every_asset_before_writing(tmp_path, kind):
    output = tmp_path / "frontend"
    assets = [_asset("a", "assets/a.png", b"one"), _asset("b", "assets/b.png", b"two")]
    files = {"assets/a.png": b"one", "assets/b.png": b"two"}
    if kind == "hash":
        files["assets/b.png"] = b"bad"
    elif kind == "size":
        files["assets/b.png"] = b"truncated"
    else:
        del files["assets/b.png"]
    with pytest.raises(BundleInstallError, match="mismatch|Missing"):
        install_bundle(_bundle(assets, files), output)
    assert not output.exists()


def test_duplicate_and_case_colliding_zip_paths_are_rejected(tmp_path):
    with pytest.raises(BundleInstallError, match="Duplicate"):
        install_bundle(_bundle(extra=("assets/STABLE-01.png", b"other")), tmp_path)


def test_rejects_corrupt_zip_and_unlisted_files(tmp_path):
    with pytest.raises(BundleInstallError, match="ZIP"):
        install_bundle(b"this is an HTTP error, not a ZIP", tmp_path)
    with pytest.raises(BundleInstallError, match="Unlisted"):
        install_bundle(_bundle(extra=("unexpected.txt", b"extra")), tmp_path)


def test_enforces_uncompressed_size_limit_before_writing(tmp_path, monkeypatch):
    import lanhu_design.install as module

    monkeypatch.setattr(module, "MAX_UNCOMPRESSED_BYTES", 16)
    with pytest.raises(BundleInstallError, match="size limit"):
        install_bundle(_bundle(), tmp_path / "frontend")
    assert not (tmp_path / "frontend").exists()


def test_remote_binary_resource_is_decoded_but_error_text_is_rejected():
    from mcp.types import BlobResourceContents, TextResourceContents

    uri = "lanhu://design/snapshot-1/bundle/bundle-1"
    bundle = _bundle()
    binary = BlobResourceContents(uri=uri, mimeType="application/zip", blob=base64.b64encode(bundle).decode())
    assert _decode_resource_contents([binary]) == bundle
    text = TextResourceContents(uri=uri, text="resource not found")
    for contents in ([text], [binary, text], []):
        with pytest.raises(BundleInstallError, match="binary resource"):
            _decode_resource_contents(contents)
    binary.blob = "not base64!!!"
    with pytest.raises(BundleInstallError, match="base64"):
        _decode_resource_contents([binary])


def test_cli_installs_local_bundle_and_reports_failure(tmp_path, capsys):
    source = tmp_path / "download.zip"
    source.write_bytes(_bundle())
    output = tmp_path / "frontend"
    assert main(["--bundle", str(source), "--output", str(output)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "complete"
    source.write_bytes(b"bad")
    assert main(["--bundle", str(source), "--output", str(output)]) == 1
    assert "installation failed" in capsys.readouterr().err
