from __future__ import annotations

import asyncio
from typing import Any

from azure_updates_mcp.server import create_mcp


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def list_updates(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("list_updates", kwargs))
        return {
            "count": 1,
            "total_matched": 1,
            "limit": 50,
            "updates": [{"title": "Update"}],
        }

    def get_filter_options(self) -> dict[str, list[str]]:
        self.calls.append(("get_filter_options", {}))
        return {
            "update_types": ["GA"],
            "services": ["Azure Storage"],
            "categories": ["Security"],
        }

    def get_rss_feed(self) -> str:
        self.calls.append(("get_rss_feed", {}))
        return "<rss />"


def test_registers_expected_tools() -> None:
    async def scenario() -> None:
        mcp = create_mcp(client=FakeClient())
        tools = await mcp._list_tools()

        assert {tool.name for tool in tools} == {
            "list_updates",
            "get_filter_options",
            "get_rss_feed",
        }

    asyncio.run(scenario())


def test_list_updates_tool_delegates_to_client() -> None:
    async def scenario() -> None:
        client = FakeClient()
        mcp = create_mcp(client=client)

        result = await mcp.call_tool(
            "list_updates",
            {"update_type": "GA", "service": "Azure Storage", "limit": 5},
        )

        assert result.structured_content == {
            "count": 1,
            "total_matched": 1,
            "limit": 50,
            "updates": [{"title": "Update"}],
        }
        assert client.calls == [
            (
                "list_updates",
                {
                    "update_type": "GA",
                    "service": "Azure Storage",
                    "category": None,
                    "q": None,
                    "since_days": None,
                    "sort": None,
                    "limit": 5,
                },
            )
        ]

    asyncio.run(scenario())


def test_rss_tool_returns_xml_text() -> None:
    async def scenario() -> None:
        client = FakeClient()
        mcp = create_mcp(client=client)

        result = await mcp.call_tool("get_rss_feed", {})

        assert result.content[0].text == "<rss />"
        assert client.calls == [("get_rss_feed", {})]

    asyncio.run(scenario())
