from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
import pytest

from azure_updates_mcp.client import AzureUpdatesClient


def _item(
    *,
    url: str,
    update_type: str,
    title: str,
    summary: str,
    services: str,
    categories: str,
    updated: datetime,
) -> str:
    stamp = updated.strftime("%Y-%m-%dT%H:%M:%SZ")
    pub = updated.strftime("%a, %d %b %Y %H:%M:%S Z")
    # The real feed escapes the "<br />" inside <description>; mirror that here.
    description = (
        f"{summary}&lt;br /&gt;Update Type: {update_type}, "
        f"Services: {services}, Categories: {categories}"
    )
    return (
        "    <item>\n"
        f'      <guid isPermaLink="true">{url}</guid>\n'
        f"      <link>{url}</link>\n"
        f"      <category>{update_type}</category>\n"
        f"      <title>{title}</title>\n"
        f"      <description>{description}</description>\n"
        f"      <pubDate>{pub}</pubDate>\n"
        f"      <a10:updated>{stamp}</a10:updated>\n"
        "    </item>\n"
    )


def _feed(*items: str) -> str:
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<rss xmlns:a10="http://www.w3.org/2005/Atom" version="2.0">\n'
        "  <channel>\n"
        "    <title>Azure Updates</title>\n"
        + "".join(items)
        + "  </channel>\n"
        "</rss>\n"
    )


NOW = datetime.now(timezone.utc)

SAMPLE_FEED = _feed(
    _item(
        url="https://example.test/a",
        update_type="GA",
        title="Azure Storage gets faster",
        summary="A storage speed boost.",
        services="Azure Storage, Virtual Machines",
        categories="Features, Services",
        updated=NOW - timedelta(days=2),
    ),
    _item(
        url="https://example.test/b",
        update_type="Deprecation",
        title="Old VM series retiring",
        summary="Please migrate soon.",
        services="Virtual Machines",
        categories="Retirements",
        updated=NOW - timedelta(days=90),
    ),
    _item(
        url="https://example.test/c",
        update_type="Preview",
        title="New networking preview",
        summary="Try the preview.",
        services="Virtual Network",
        categories="",
        updated=NOW - timedelta(days=5),
    ),
)


def make_client(feed_text: str = SAMPLE_FEED) -> AzureUpdatesClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=feed_text, headers={"content-type": "application/xml"})

    return AzureUpdatesClient(
        http_client=httpx.Client(
            base_url="https://example.test",
            transport=httpx.MockTransport(handler),
        )
    )


def test_from_env_uses_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_UPDATES_BASE_URL", "https://mirror.example.test/")

    client = AzureUpdatesClient.from_env()

    assert client.base_url == "https://mirror.example.test"
    client.close()


def test_get_rss_feed_returns_raw_xml() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, text="<rss />")

    client = AzureUpdatesClient(
        http_client=httpx.Client(
            base_url="https://example.test",
            transport=httpx.MockTransport(handler),
        )
    )

    assert client.get_rss_feed() == "<rss />"
    assert requests[0].url.path == "/rss/updates"


def test_list_updates_parses_items_and_metadata() -> None:
    result = make_client().list_updates()

    assert result["total_matched"] == 3
    assert result["count"] == 3
    first = result["updates"][0]
    assert first["title"] == "Azure Storage gets faster"
    assert first["url"] == "https://example.test/a"
    assert first["update_type"] == "GA"
    assert first["services"] == ["Azure Storage", "Virtual Machines"]
    assert first["categories"] == ["Features", "Services"]
    assert first["summary"] == "A storage speed boost."
    assert "_dt" not in first


def test_list_updates_sorts_newest_first_by_default() -> None:
    urls = [item["url"] for item in make_client().list_updates()["updates"]]
    assert urls == [
        "https://example.test/a",
        "https://example.test/c",
        "https://example.test/b",
    ]


def test_list_updates_sort_oldest() -> None:
    urls = [item["url"] for item in make_client().list_updates(sort="oldest")["updates"]]
    assert urls == [
        "https://example.test/b",
        "https://example.test/c",
        "https://example.test/a",
    ]


def test_filter_by_update_type_is_case_insensitive() -> None:
    result = make_client().list_updates(update_type="ga")
    assert [item["url"] for item in result["updates"]] == ["https://example.test/a"]


def test_filter_by_service_substring() -> None:
    result = make_client().list_updates(service="virtual machines")
    assert {item["url"] for item in result["updates"]} == {
        "https://example.test/a",
        "https://example.test/b",
    }


def test_filter_by_category() -> None:
    result = make_client().list_updates(category="Retirements")
    assert [item["url"] for item in result["updates"]] == ["https://example.test/b"]


def test_free_text_search_matches_summary() -> None:
    result = make_client().list_updates(q="migrate")
    assert [item["url"] for item in result["updates"]] == ["https://example.test/b"]


def test_since_days_filters_older_updates() -> None:
    result = make_client().list_updates(since_days=7)
    assert {item["url"] for item in result["updates"]} == {
        "https://example.test/a",
        "https://example.test/c",
    }


def test_limit_reports_total_matched() -> None:
    result = make_client().list_updates(limit=1)
    assert result["count"] == 1
    assert result["total_matched"] == 3
    assert result["limit"] == 1
    assert result["updates"][0]["url"] == "https://example.test/a"


def test_get_filter_options_returns_sorted_distinct_values() -> None:
    options = make_client().get_filter_options()
    assert options["update_types"] == ["Deprecation", "GA", "Preview"]
    assert options["services"] == ["Azure Storage", "Virtual Machines", "Virtual Network"]
    assert options["categories"] == ["Features", "Retirements", "Services"]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"limit": 201}, "limit"),
        ({"since_days": 366}, "since_days"),
        ({"sort": "alphabetical"}, "sort"),
    ],
)
def test_list_updates_validates_documented_bounds(
    kwargs: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        make_client().list_updates(**kwargs)
