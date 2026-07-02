# azure-updates-mcp

MCP server for [Azure updates](https://azurecharts.com/updates), backed by the public
Azure Charts / [aka.ms/aztty](https://aka.ms/aztty) RSS feed.

## Prerequisites

- [Python 3.13 or newer](https://www.python.org/downloads/) is required by the package.
- [uv](https://docs.astral.sh/uv/getting-started/installation/) is used for installation and development. The provided install scripts install `uv` automatically if it is missing.
- [Git](https://git-scm.com/downloads) is required when installing directly from the GitHub repository.

## Install

Windows PowerShell:

```powershell
irm https://raw.githubusercontent.com/aryxenv/azure-updates-mcp/main/scripts/install.ps1 | iex
```

macOS/Linux:

```sh
curl -fsSL https://raw.githubusercontent.com/aryxenv/azure-updates-mcp/main/scripts/install.sh | bash
```

Manual install with `uv`:

```sh
uv tool install --force git+https://github.com/aryxenv/azure-updates-mcp.git
uv tool update-shell
```

## MCP stdio configuration

Configure your MCP client to start the server with:

```json
{
  "mcpServers": {
    "azure-updates": {
      "command": "azure-updates-mcp",
      "args": ["start"]
    }
  }
}
```

## Tools

- `list_updates`: List Azure updates with optional filters, search, sorting, and a result limit.
  Filter by `update_type` (Announcement, GA, Preview, Deprecation), `service`
  (e.g. `Virtual Machines`), `category` (e.g. `Security`, `Retirements`), free-text `q`,
  and `since_days`. Returns structured items (title, url, update type, services,
  categories, summary, dates) plus `total_matched` and the applied `limit`.
- `get_filter_options`: Get the update types, services, and categories currently present in the feed.
- `get_rss_feed`: Get the raw Azure Updates RSS feed XML.

### Filtering

The upstream feed is a single RSS document, so filtering is applied by the server
after fetching the feed. This lets an agent narrow results with the `list_updates`
parameters above without any query support on the source. Call `get_filter_options`
first to discover valid `service` and `category` values.

## Development

```sh
uv sync --dev
uv run pytest
uv run azure-updates-mcp start
```

The server uses `https://aztty.azurewebsites.net` by default. For tests or mirrors, pass `--base-url` to `azure-updates-mcp start` or set `AZURE_UPDATES_BASE_URL`.

## Acknowledgements

Azure update data is provided by [Azure Charts](https://azurecharts.com/) and exposed as a
feed via Azure Terminal ([aka.ms/aztty](https://aka.ms/aztty)) at
`https://aztty.azurewebsites.net/rss/updates`.
