"""Command-line entry point for the Azure Updates MCP server."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from azure_updates_mcp.server import create_mcp


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="azure-updates-mcp")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start", help="Start the MCP server over stdio")
    start_parser.add_argument(
        "--base-url",
        default=None,
        help=(
            "Azure Updates base URL. Defaults to AZURE_UPDATES_BASE_URL or "
            "https://aztty.azurewebsites.net."
        ),
    )

    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command == "start":
        create_mcp(base_url=args.base_url).run(transport="stdio")
