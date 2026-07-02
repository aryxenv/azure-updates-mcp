from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_windows_installer_uses_uv_tool_install() -> None:
    text = (ROOT / "scripts" / "install.ps1").read_text(encoding="utf-8")

    assert "uv tool install --force" in text
    assert "https://github.com/aryxenv/azure-updates-mcp.git" in text
    assert '"git+$RepoUrl"' in text
    assert "uv tool update-shell" in text


def test_unix_installer_uses_uv_tool_install() -> None:
    text = (ROOT / "scripts" / "install.sh").read_text(encoding="utf-8")

    assert "uv tool install --force" in text
    assert "https://github.com/aryxenv/azure-updates-mcp.git" in text
    assert '"git+$REPO_URL"' in text
    assert "uv tool update-shell" in text
