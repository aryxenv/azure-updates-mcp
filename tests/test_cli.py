from __future__ import annotations

from typing import Any

from azure_updates_mcp import cli


def test_start_command_runs_stdio(monkeypatch: Any) -> None:
    calls: dict[str, Any] = {}

    class FakeMcp:
        def run(self, **kwargs: Any) -> None:
            calls["run"] = kwargs

    def fake_create_mcp(*, base_url: str | None) -> FakeMcp:
        calls["base_url"] = base_url
        return FakeMcp()

    monkeypatch.setattr(cli, "create_mcp", fake_create_mcp)

    cli.main(["start", "--base-url", "https://example.test"])

    assert calls == {
        "base_url": "https://example.test",
        "run": {"transport": "stdio"},
    }
