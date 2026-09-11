"""Exercise installed-style, non-interactive startup without real credentials or network."""

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def installed_runtime(tmp_path):
    package_dir = tmp_path / "site-packages"
    package_dir.mkdir()
    shutil.copy2(ROOT / "lanhu_mcp_server.py", package_dir)
    shutil.copytree(ROOT / "lanhu_design", package_dir / "lanhu_design",
                    ignore=shutil.ignore_patterns("__pycache__"))
    working_dir = tmp_path / "project"
    working_dir.mkdir()
    launcher = tmp_path / "bin" / "lanhu-mcp"
    launcher.parent.mkdir()
    launcher.write_text(
        "import json, sys\n"
        "from pathlib import Path\n"
        "sys.path.insert(0, sys.argv.pop(1))\n"
        "import lanhu_mcp_server as server\n"
        "def capture_run(**kwargs):\n"
        "    result = dict(cookie=server.COOKIE, config=str(server.env_path), **kwargs)\n"
        "    Path('runtime.json').write_text(json.dumps(result), encoding='utf-8')\n"
        "server.mcp.run = capture_run\n"
        "server.main()\n",
        encoding="utf-8",
    )
    # Never inherit a local account's credentials/configuration into the test process.
    env = {key: value for key, value in os.environ.items()
           if key not in {"LANHU_ENV_FILE", "LANHU_COOKIE", "DDS_COOKIE", "FEISHU_WEBHOOK_URL",
                          "MCP_TRANSPORT", "SERVER_HOST", "SERVER_PORT", "DATA_DIR", "PYTHONPATH"}}
    env["DATA_DIR"] = str(tmp_path / "data")

    def launch(extra_env=None):
        return subprocess.run(
            [sys.executable, str(launcher), str(package_dir), "--transport", "stdio"],
            cwd=working_dir,
            env={**env, **(extra_env or {})},
            capture_output=True, text=True, timeout=45,
        )

    return SimpleNamespace(package_dir=package_dir, cwd=working_dir, launch=launch, root=tmp_path)


@pytest.mark.parametrize("case,expected_cookie", [
    ("working_directory", "fake-working-cookie"),
    ("package_sidecar", "fake-package-cookie"),
    ("explicit_file", "fake-explicit-cookie"),
    ("explicit_relative_file", "fake-explicit-cookie"),
    ("process_environment", "fake-process-cookie"),
    ("no_parent_search", "your_lanhu_cookie_here"),
])
def test_installed_launcher_configuration(installed_runtime, case, expected_cookie):
    runtime = installed_runtime
    # A parent .env must never be discovered implicitly by python-dotenv.
    (runtime.root / ".env").write_text("LANHU_COOKIE=fake-parent-cookie\n", encoding="utf-8")
    extra_env = {}
    expected_path = runtime.cwd / ".env"
    if case != "no_parent_search":
        expected_path.write_text("LANHU_COOKIE=fake-working-cookie\n", encoding="utf-8")
    if case in {"package_sidecar", "explicit_file", "explicit_relative_file", "process_environment"}:
        expected_path = runtime.package_dir / ".env"
        expected_path.write_text("LANHU_COOKIE=fake-package-cookie\n", encoding="utf-8")
    if case in {"explicit_file", "explicit_relative_file", "process_environment"}:
        explicit = runtime.cwd / "config.env"
        explicit.write_text("LANHU_COOKIE=fake-explicit-cookie\n", encoding="utf-8")
        expected_path = Path("config.env") if case == "explicit_relative_file" else explicit
        extra_env["LANHU_ENV_FILE"] = str(expected_path)
    if case == "process_environment":
        extra_env["LANHU_COOKIE"] = "fake-process-cookie"

    result = runtime.launch(extra_env)

    assert result.returncode == 0, result.stderr
    assert result.stdout == "", "stdio startup must reserve stdout for MCP protocol messages"
    receipt = json.loads((runtime.cwd / "runtime.json").read_text(encoding="utf-8"))
    assert receipt["cookie"] == expected_cookie
    assert receipt["config"] == str(expected_path)
    assert receipt["transport"] == "stdio"


def test_installed_launcher_rejects_missing_explicit_configuration(installed_runtime):
    runtime = installed_runtime
    (runtime.cwd / ".env").write_text("LANHU_COOKIE=fake-fallback-cookie\n", encoding="utf-8")
    missing = runtime.cwd / "missing.env"

    result = runtime.launch({"LANHU_ENV_FILE": str(missing)})

    assert result.returncode != 0
    assert "LANHU_ENV_FILE is not a file" in result.stderr
    assert result.stdout == ""
    assert not (runtime.cwd / "runtime.json").exists()


@pytest.fixture
def notification_server(tmp_path, monkeypatch):
    config = tmp_path / "fake.env"
    config.write_text("LANHU_COOKIE=fake-notification-cookie\n", encoding="utf-8")
    monkeypatch.setenv("LANHU_ENV_FILE", str(config))
    monkeypatch.setenv("LANHU_COOKIE", "fake-notification-cookie")
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    name = "_lanhu_notification_runtime_test"
    spec = importlib.util.spec_from_file_location(name, ROOT / "lanhu_mcp_server.py")
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("outcome,expected", [
    ("known_mention", True), ("unknown_mention", True),
    ("rejected", False), ("exception", False),
])
async def test_notification_diagnostics_use_stderr_only(notification_server, monkeypatch, capsys,
                                                       outcome, expected):
    server = notification_server
    calls = []

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, **kwargs):
            calls.append((url, kwargs))
            if outcome == "exception":
                raise RuntimeError("simulated notification error")
            return SimpleNamespace(json=lambda: {"code": 1 if outcome == "rejected" else 0})

    monkeypatch.setattr(server.httpx, "AsyncClient", lambda **kwargs: FakeClient())
    monkeypatch.setattr(server, "FEISHU_USER_ID_MAP", {"FixtureUser": "fake-user-id"})
    monkeypatch.setattr(server, "FEISHU_WEBHOOK_URL", "https://example.invalid/no-request")
    capsys.readouterr()

    result = await server.send_feishu_notification(
        summary="Test notification", content="Fixture content", author_name="Fixture author",
        author_role="Developer", mentions=["Unknown" if outcome == "unknown_mention" else "FixtureUser"],
        message_type="normal",
    )

    output = capsys.readouterr()
    assert result is expected
    assert len(calls) == 1
    assert output.out == ""
    assert "飞书通知" in output.err
