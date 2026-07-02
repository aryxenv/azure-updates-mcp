"""FastMCP server for Azure Updates."""

from __future__ import annotations

from typing import Any, Literal

from fastmcp import FastMCP

from azure_updates_mcp.client import AzureUpdatesClient


def create_mcp(
    *,
    client: AzureUpdatesClient | None = None,
    base_url: str | None = None,
) -> FastMCP:
    azure_updates = client or (
        AzureUpdatesClient(base_url=base_url) if base_url else AzureUpdatesClient.from_env()
    )
    mcp = FastMCP("Azure Updates")

    @mcp.tool
    def list_updates(
        update_type: str | None = None,
        service: str | None = None,
        category: str | None = None,
        q: str | None = None,
        since_days: int | None = None,
        sort: Literal["newest", "oldest"] | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """List Azure updates from the RSS feed with optional filters, search, sort, and a result limit.

        Args:
            update_type: Match the update type, e.g. "Announcement", "GA", "Preview",
                or "Deprecation" (case-insensitive, exact match).
            service: Match an Azure service, e.g. "Virtual Machines" or "Azure Storage"
                (case-insensitive substring match against the services on each update).
            category: Match a category, e.g. "Security", "Features", or "Retirements"
                (case-insensitive substring match).
            q: Free-text search across the update title and summary.
            since_days: Only include updates published within the last N days (1-365).
            sort: "newest" (default) or "oldest".
            limit: Maximum number of updates to return (1-200, default 50).
                ``total_matched`` reports how many matched before the limit was applied.

        Use ``get_filter_options`` to discover the update types, services, and
        categories currently present in the feed.
        """
        return azure_updates.list_updates(
            update_type=update_type,
            service=service,
            category=category,
            q=q,
            since_days=since_days,
            sort=sort,
            limit=limit,
        )

    @mcp.tool
    def get_filter_options() -> dict[str, list[str]]:
        """Get the update types, services, and categories currently present in the Azure updates feed."""
        return azure_updates.get_filter_options()

    @mcp.tool
    def get_rss_feed() -> str:
        """Get the raw Azure Updates RSS feed XML."""
        return azure_updates.get_rss_feed()

    return mcp
