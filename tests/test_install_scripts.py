"""Regression checks for the source checkout installers."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("script", ["easy-install.sh", "quickstart.sh", "run-stdio.sh"])
def test_posix_install_scripts_have_valid_bash_syntax(script):
    subprocess.run(["bash", "-n", str(ROOT / script)], check=True)


def test_easy_installer_rejects_python_39_before_creating_venv(tmp_path):
    installer = tmp_path / "easy-install.sh"
    shutil.copy2(ROOT / "easy-install.sh", installer)
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_python = """#!/bin/sh
case "$*" in
  *"raise SystemExit"*) exit 1 ;;
  *"version_info[:3]"*) echo 3.9.6; exit 0 ;;
esac
exit 1
"""
    for name in ("python3", "python", "python3.13", "python3.12", "python3.11", "python3.10"):
        executable = fake_bin / name
        executable.write_text(fake_python, encoding="utf-8")
        executable.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{os.defpath}"
    env["TERM"] = "dumb"
    caller_dir = tmp_path / "caller"
    caller_dir.mkdir()
    result = subprocess.run(
        ["bash", str(installer)],
        cwd=caller_dir,
        env=env,
        input="\n",
        text=True,
        capture_output=True,
        timeout=10,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert "Python 3.10" in output
    assert "3.9.6" in output
    assert not (tmp_path / "venv").exists()
    assert not (caller_dir / "venv").exists()


def test_easy_installer_falls_back_between_package_indexes(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    shutil.copy2(ROOT / "easy-install.sh", repo / "easy-install.sh")
    (repo / ".env").write_text('LANHU_COOKIE="session=test"\n', encoding="utf-8")

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    mirror_log = tmp_path / "mirrors.log"
    browser_log = tmp_path / "browsers.log"
    venv_template = tmp_path / "venv-python"
    venv_template.write_text(
        r"""#!/bin/sh
case "$*" in
  *"version_info >= (3, 10)"*) exit 0 ;;
  *"version_info[:3]"*) echo 3.14.6; exit 0 ;;
  *"-m pip install"*)
    echo "$PIP_INDEX_URL" >> "$MIRROR_LOG"
    case "$PIP_INDEX_URL" in
      *mirrors.aliyun.com*) exit 1 ;;
      *pypi.tuna.tsinghua.edu.cn*) exit 0 ;;
      *) exit 9 ;;
    esac ;;
  *"-m pip check"*) exit 0 ;;
  *"-m playwright install chromium"*)
    echo "${PLAYWRIGHT_DOWNLOAD_HOST:-official}|${PLAYWRIGHT_CHROMIUM_DOWNLOAD_HOST:-none}" >> "$BROWSER_LOG"
    case "$PLAYWRIGHT_DOWNLOAD_HOST|$PLAYWRIGHT_CHROMIUM_DOWNLOAD_HOST" in
      *binaries/playwright*\|*binaries/chrome-for-testing*) exit 1 ;;
      *binaries/playwright*\|) exit 1 ;;
      "|") exit 0 ;;
      *) exit 9 ;;
    esac ;;
esac
exit 0
""",
        encoding="utf-8",
    )
    venv_template.chmod(0o755)
    fake_python = fake_bin / "python3"
    fake_python.write_text(
        """#!/bin/sh
case "$*" in
  *"version_info >= (3, 10)"*) exit 0 ;;
  *"version_info[:3]"*) echo 3.14.6; exit 0 ;;
  *"-m pip --version"*) echo 'pip 26.1'; exit 0 ;;
  *"-m venv venv"*)
    mkdir -p venv/bin
    cp "$FAKE_VENV_TEMPLATE" venv/bin/python
    chmod +x venv/bin/python
    exit 0 ;;
esac
exit 1
""",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    for name in ("python", "python3.13", "python3.12", "python3.11", "python3.10"):
        (fake_bin / name).symlink_to(fake_python)
    fake_open = fake_bin / "open"
    fake_open.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    fake_open.chmod(0o755)

    caller = tmp_path / "caller"
    caller.mkdir()
    env = os.environ.copy()
    env.update(
        PATH=f"{fake_bin}{os.pathsep}{os.defpath}",
        TERM="dumb",
        MIRROR_LOG=str(mirror_log),
        BROWSER_LOG=str(browser_log),
        FAKE_VENV_TEMPLATE=str(venv_template),
    )
    env.pop("PIP_INDEX_URL", None)
    env.pop("PLAYWRIGHT_DOWNLOAD_HOST", None)
    env.pop("PLAYWRIGHT_CHROMIUM_DOWNLOAD_HOST", None)
    result = subprocess.run(
        ["bash", str(repo / "easy-install.sh")],
        cwd=caller,
        env=env,
        input="\nn\n\nn\n",
        text=True,
        capture_output=True,
        timeout=20,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert mirror_log.read_text(encoding="utf-8").splitlines() == [
        "https://mirrors.aliyun.com/pypi/simple",
        "https://pypi.tuna.tsinghua.edu.cn/simple",
    ]
    assert browser_log.read_text(encoding="utf-8").splitlines() == [
        "https://cdn.npmmirror.com/binaries/playwright|https://cdn.npmmirror.com/binaries/chrome-for-testing",
        "https://cdn.npmmirror.com/binaries/playwright|none",
        "official|none",
    ]
    assert "自动回退 Playwright 官方 CDN" in result.stdout
    assert (repo / "venv").is_dir()
    assert not (caller / "venv").exists()


def test_installers_install_the_package_and_default_to_domestic_mirrors():
    for filename in ("easy-install.sh", "quickstart.sh"):
        content = (ROOT / filename).read_text(encoding="utf-8")
        assert "pip install --timeout 60 --retries 5 -e ." in content
        assert "pip install --upgrade pip" not in content
        assert "https://mirrors.aliyun.com/pypi/simple" in content
        assert "https://pypi.tuna.tsinghua.edu.cn/simple" in content
        assert content.index("mirrors.aliyun.com") < content.index("pypi.tuna.tsinghua.edu.cn")
        assert "https://pypi.org/simple" in content
        assert "https://cdn.npmmirror.com/binaries/playwright" in content
        assert "https://cdn.npmmirror.com/binaries/chrome-for-testing" in content
        assert "PLAYWRIGHT_CHROMIUM_DOWNLOAD_HOST" in content
        assert "env -u PLAYWRIGHT_DOWNLOAD_HOST" in content
        assert "自动回退 Playwright 官方 CDN" in content
        assert "SCRIPT_DIR" in content

    for filename in ("easy-install.bat", "quickstart.bat"):
        content = (ROOT / filename).read_text(encoding="utf-8")
        assert "pip install --timeout 60 --retries 5 -e ." in content
        assert "pip install --upgrade pip" not in content
        assert "https://mirrors.aliyun.com/pypi/simple" in content
        assert "https://pypi.tuna.tsinghua.edu.cn/simple" in content
        assert content.index("mirrors.aliyun.com") < content.index("pypi.tuna.tsinghua.edu.cn")
        assert "https://pypi.org/simple" in content
        assert "https://cdn.npmmirror.com/binaries/playwright" in content
        assert "https://cdn.npmmirror.com/binaries/chrome-for-testing" in content
        assert "PLAYWRIGHT_CHROMIUM_DOWNLOAD_HOST" in content
        assert 'set "PLAYWRIGHT_DOWNLOAD_HOST="' in content
        assert "自动回退 Playwright 官方 CDN" in content
        assert 'cd /d "%~dp0"' in content
        assert "PYTHON_MAJOR" in content
        assert "VENV_PYTHON_MAJOR" in content
        assert "^>=" not in content

    windows_installer = (ROOT / "easy-install.bat").read_text(encoding="utf-8")
    assert "LANHU_INSTALL_NONINTERACTIVE" in windows_installer
    assert "LANHU_SKIP_BROWSER_INSTALL" in windows_installer
    assert not any(line.strip() == "pause" for line in windows_installer.splitlines())


def test_windows_install_is_a_release_gate():
    workflow = (ROOT / ".github" / "workflows" / "verify.yml").read_text(encoding="utf-8")
    assert "windows-install:" in workflow
    assert "runs-on: windows-latest" in workflow
    assert "easy-install.bat" in workflow
    assert "playwright install chromium" in workflow
    assert "Windows Chromium launch succeeded" in workflow
    assert "Windows MCP stdio handshake exposed 18 tools" in workflow
    assert "needs: [tests, windows-install]" in workflow


def test_stdio_launcher_reports_missing_install(tmp_path):
    launcher = tmp_path / "run-stdio.sh"
    shutil.copy2(ROOT / "run-stdio.sh", launcher)
    result = subprocess.run(
        ["bash", str(launcher)],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 1
    assert "easy-install.sh" in result.stderr
