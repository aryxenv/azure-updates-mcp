#!/usr/bin/env sh
set -eu

REPO_URL="${AZURE_UPDATES_MCP_REPO:-https://github.com/aryxenv/azure-updates-mcp.git}"

if ! command -v uv >/dev/null 2>&1; then
    echo "uv was not found. Installing uv first..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

uv tool install --force "git+$REPO_URL"
uv tool update-shell

TOOL_BIN="$(uv tool dir --bin)"
echo
echo "Azure Updates MCP installed."
echo "Start command: azure-updates-mcp start"
echo "If your current shell cannot find it yet, restart the shell or run:"
echo "  export PATH=\"$TOOL_BIN:\$PATH\""
