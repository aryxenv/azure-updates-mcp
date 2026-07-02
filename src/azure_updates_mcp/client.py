"""HTTP client for the public Azure Updates feed (Azure Charts via aka.ms/aztty)."""

from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

DEFAULT_BASE_URL = "https://aztty.azurewebsites.net"

_ATOM_UPDATED = "{http://www.w3.org/2005/Atom}updated"
_MIN_DT = datetime.min.replace(tzinfo=timezone.utc)

# The feed appends a metadata trailer to each description, e.g.
#   "<br />Update Type: GA, Services: Virtual Machines, Categories: Features"
_TRAILER_SPLIT_RE = re.compile(r"<br\s*/?>\s*Update Type:", re.IGNORECASE)
_TRAILER_META_RE = re.compile(
    r"Services:\s*(?P<services>.*?),\s*Categories:\s*(?P<categories>.*?)\s*$",
    re.DOTALL,
)
_TRAILING_BR_RE = re.compile(r"(?:<br\s*/?>)+\s*$", re.IGNORECASE)


def _split_list(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _clean_summary(text: str) -> str:
    return _TRAILING_BR_RE.sub("", text.strip()).strip()


class AzureUpdatesClient:
    """Small synchronous client for the Azure Updates RSS feed."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        *,
        timeout: float = 30.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = http_client or httpx.Client(base_url=self.base_url, timeout=timeout)

    @classmethod
    def from_env(cls) -> "AzureUpdatesClient":
        return cls(os.environ.get("AZURE_UPDATES_BASE_URL", DEFAULT_BASE_URL))

    def close(self) -> None:
        self._client.close()

    def get_rss_feed(self) -> str:
        """Return the raw Azure Updates RSS feed XML."""
        return self._get_text("/rss/updates")

    def list_updates(
        self,
        *,
        update_type: str | None = None,
        service: str | None = None,
        category: str | None = None,
        q: str | None = None,
        since_days: int | None = None,
        sort: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        self._validate_range("since_days", since_days, 1, 365)
        self._validate_range("limit", limit, 1, 200)
        self._validate_choice("sort", sort, {"newest", "oldest"})

        updates = self._parse_feed(self.get_rss_feed())
        matched = self._filter_updates(
            updates,
            update_type=update_type,
            service=service,
            category=category,
            q=q,
            since_days=since_days,
        )

        matched.sort(key=lambda item: item["_dt"] or _MIN_DT, reverse=sort != "oldest")

        effective_limit = 50 if limit is None else limit
        limited = matched[:effective_limit]
        return {
            "count": len(limited),
            "total_matched": len(matched),
            "limit": effective_limit,
            "updates": [self._public_update(item) for item in limited],
        }

    def get_filter_options(self) -> dict[str, list[str]]:
        updates = self._parse_feed(self.get_rss_feed())
        update_types: set[str] = set()
        services: set[str] = set()
        categories: set[str] = set()
        for item in updates:
            if item["update_type"]:
                update_types.add(item["update_type"])
            services.update(item["services"])
            categories.update(item["categories"])
        return {
            "update_types": sorted(update_types),
            "services": sorted(services),
            "categories": sorted(categories),
        }

    @classmethod
    def _parse_feed(cls, xml_text: str) -> list[dict[str, Any]]:
        # Encode to bytes so ElementTree accepts feeds that carry an XML
        # encoding declaration (it rejects such declarations on str input).
        root = ET.fromstring(xml_text.encode("utf-8"))
        channel = root.find("channel")
        if channel is None:
            return []

        updates: list[dict[str, Any]] = []
        for item in channel.findall("item"):
            description = item.findtext("description") or ""
            summary, services, categories = cls._parse_description(description)
            published = (item.findtext("pubDate") or "").strip()
            updated = (item.findtext(_ATOM_UPDATED) or "").strip()
            updates.append(
                {
                    "title": (item.findtext("title") or "").strip(),
                    "url": (item.findtext("link") or "").strip(),
                    "update_type": (item.findtext("category") or "").strip(),
                    "services": services,
                    "categories": categories,
                    "summary": summary,
                    "published": published,
                    "updated": updated,
                    "_dt": cls._parse_dt(updated, published),
                }
            )
        return updates

    @classmethod
    def _parse_description(cls, description: str) -> tuple[str, list[str], list[str]]:
        parts = _TRAILER_SPLIT_RE.split(description, maxsplit=1)
        summary = _clean_summary(parts[0])
        services: list[str] = []
        categories: list[str] = []
        if len(parts) == 2:
            match = _TRAILER_META_RE.search(parts[1])
            if match:
                services = _split_list(match.group("services"))
                categories = _split_list(match.group("categories"))
        return summary, services, categories

    @staticmethod
    def _parse_dt(iso_value: str, rfc_value: str) -> datetime | None:
        parsed: datetime | None = None
        if iso_value:
            try:
                parsed = datetime.fromisoformat(iso_value.replace("Z", "+00:00"))
            except ValueError:
                parsed = None
        if parsed is None and rfc_value:
            try:
                parsed = parsedate_to_datetime(rfc_value)
            except (TypeError, ValueError):
                parsed = None
        if parsed is not None and parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed

    @staticmethod
    def _filter_updates(
        updates: list[dict[str, Any]],
        *,
        update_type: str | None,
        service: str | None,
        category: str | None,
        q: str | None,
        since_days: int | None,
    ) -> list[dict[str, Any]]:
        wanted_type = update_type.strip().lower() if update_type else None
        wanted_service = service.strip().lower() if service else None
        wanted_category = category.strip().lower() if category else None
        query = q.strip().lower() if q else None
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=since_days)
            if since_days is not None
            else None
        )

        result: list[dict[str, Any]] = []
        for item in updates:
            if wanted_type and item["update_type"].lower() != wanted_type:
                continue
            if wanted_service and not any(
                wanted_service in service_name.lower() for service_name in item["services"]
            ):
                continue
            if wanted_category and not any(
                wanted_category in category_name.lower() for category_name in item["categories"]
            ):
                continue
            if query and query not in item["title"].lower() and query not in item["summary"].lower():
                continue
            if cutoff is not None and (item["_dt"] is None or item["_dt"] < cutoff):
                continue
            result.append(item)
        return result

    @staticmethod
    def _public_update(item: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in item.items() if not key.startswith("_")}

    def _get_text(self, path: str, params: dict[str, Any] | None = None) -> str:
        response = self._client.get(
            path,
            params=params,
            headers={"Accept": "application/rss+xml, application/xml, text/xml"},
        )
        response.raise_for_status()
        return response.text

    @staticmethod
    def _validate_range(name: str, value: int | None, minimum: int, maximum: int | None) -> None:
        if value is None:
            return
        if value < minimum or (maximum is not None and value > maximum):
            if maximum is None:
                raise ValueError(f"{name} must be at least {minimum}")
            raise ValueError(f"{name} must be between {minimum} and {maximum}")

    @staticmethod
    def _validate_choice(name: str, value: str | None, choices: set[str]) -> None:
        if value is not None and value not in choices:
            allowed = ", ".join(sorted(choices))
            raise ValueError(f"{name} must be one of: {allowed}")
