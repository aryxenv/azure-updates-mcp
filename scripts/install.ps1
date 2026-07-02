$ErrorActionPreference = "Stop"

$RepoUrl = $env:AZURE_UPDATES_MCP_REPO
if ([string]::IsNullOrWhiteSpace($RepoUrl)) {
    $RepoUrl = "https://github.com/aryxenv/azure-updates-mcp.git"
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "uv was not found. Installing uv first..."
    irm https://astral.sh/uv/install.ps1 | iex
}

uv tool install --force "git+$RepoUrl"
uv tool update-shell

$ToolBin = (uv tool dir --bin).Trim()
Write-Host ""
Write-Host "Azure Updates MCP installed."
Write-Host "Start command: azure-updates-mcp start"
Write-Host "If your current shell cannot find it yet, restart the shell or run:"
Write-Host "  `$env:Path = `"$ToolBin;`$env:Path`""
