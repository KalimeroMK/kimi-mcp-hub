# Kimi MCP Hub - One-line installer for Windows (PowerShell)
# Usage:
#   iwr -useb https://raw.githubusercontent.com/KalimeroMK/kimi-mcp-hub/main/install/install.ps1 | iex
#   iwr -useb https://raw.githubusercontent.com/KalimeroMK/kimi-mcp-hub/main/install/install.ps1 | & ([scriptblock]::create($_)) -Yes

[CmdletBinding()]
param(
    [switch]$Yes
)

$REPO = "KalimeroMK/kimi-mcp-hub"
$INSTALL_DIR = if ($env:KIMI_MCP_HUB_DIR) { $env:KIMI_MCP_HUB_DIR } else { "$env:USERPROFILE\.kimi-mcp-hub" }

function Write-Header {
    Write-Host ""
    Write-Host "  KIMI MCP HUB" -ForegroundColor Cyan -NoNewline
    Write-Host " - One-click MCP server & skills manager" -ForegroundColor Gray
    Write-Host "  23 MCP Servers | 34 AI Skills | Persistent Memory" -ForegroundColor DarkGray
    Write-Host ""
}

function Check-Requirements {
    Write-Host "Checking requirements..." -ForegroundColor Cyan
    
    # Check Python
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $pyVersion = (python --version 2>&1).ToString().Split()[1]
        Write-Host "  Python $pyVersion found" -ForegroundColor Green
    } elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
        $pyVersion = (python3 --version 2>&1).ToString().Split()[1]
        Write-Host "  Python $pyVersion found" -ForegroundColor Green
    } else {
        Write-Host "  Python 3.10+ is required. Install from https://python.org/downloads" -ForegroundColor Red
        exit 1
    }
    
    # Check pip
    if (python -m pip --version -ErrorAction SilentlyContinue) {
        Write-Host "  pip found" -ForegroundColor Green
    } else {
        Write-Host "  pip not found. Run: python -m ensurepip --upgrade" -ForegroundColor Red
        exit 1
    }
    
    # Check Node.js (optional)
    if (Get-Command node -ErrorAction SilentlyContinue) {
        $nodeVersion = (node --version 2>$null)
        Write-Host "  Node.js $nodeVersion found" -ForegroundColor Green
    } else {
        Write-Host "  Node.js not found (needed for some MCP servers)" -ForegroundColor Yellow
    }
}

function Install-FromGitHub {
    Write-Host "Installing from GitHub..." -ForegroundColor Cyan
    
    # Remove old install if exists
    if (Test-Path $INSTALL_DIR) {
        Remove-Item -Recurse -Force $INSTALL_DIR
    }
    
    git clone --depth 1 "https://github.com/$REPO.git" $INSTALL_DIR
    Write-Host "  Cloned to $INSTALL_DIR" -ForegroundColor Green
    
    Set-Location $INSTALL_DIR
    python -m pip install --upgrade --user -e .
    Write-Host "  Package installed" -ForegroundColor Green
}

function Install-PipGit {
    Write-Host "Installing directly from GitHub (pip)..." -ForegroundColor Cyan
    python -m pip install --upgrade --user "git+https://github.com/$REPO.git"
    Write-Host "  Installed from GitHub" -ForegroundColor Green
}

function Show-Welcome {
    Write-Host ""
    Write-Host "Kimi MCP Hub installed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Quick start:" -ForegroundColor Cyan
    Write-Host "  kimi-mcp-hub init      # Run interactive setup wizard"
    Write-Host "  kimi-mcp-hub status    # Check installation status"
    Write-Host "  kimi-mcp-hub doctor    # Check system health"
    Write-Host ""
    Write-Host "Add your first server:" -ForegroundColor Cyan
    Write-Host "  kimi-mcp-hub add github"
    Write-Host "  kimi-mcp-hub auth github  # Auto-browser OAuth"
    Write-Host ""
    Write-Host "Use in Kimi CLI:" -ForegroundColor Cyan
    Write-Host "  /mcp       # List available tools"
    Write-Host "  /skills    # List installed skills"
    Write-Host ""
    if ($Yes) {
        Write-Host "Install with auto CLAUDE.md support:" -ForegroundColor Cyan
        Write-Host "  iwr -useb .../install.ps1 | & ([scriptblock]::create(`$_)) -Yes"
        Write-Host ""
    }
}

function Apply-ClaudeCompat {
    Write-Host "Applying claude-compat patch (auto-load CLAUDE.md and CLAUDE.local.md)..." -ForegroundColor Cyan
    $kimi = Get-Command kimi-mcp-hub -ErrorAction SilentlyContinue
    if ($kimi) {
        & kimi-mcp-hub claude-compat --yes
    } else {
        Write-Host "  kimi-mcp-hub not found in PATH. Skipping claude-compat patch." -ForegroundColor Yellow
        Write-Host "  Run manually after adding it to PATH: kimi-mcp-hub claude-compat --yes" -ForegroundColor Gray
    }
}

# Main
Write-Header
Check-Requirements
Install-PipGit
if ($Yes) {
    Apply-ClaudeCompat
}
Show-Welcome
