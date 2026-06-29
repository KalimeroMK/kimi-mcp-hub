# Kimi MCP Hub - One-line installer for Windows (PowerShell)
# Usage:
#   iwr -useb https://raw.githubusercontent.com/KalimeroMK/kimi-mcp-hub/main/install/install.ps1 | iex
#   iwr -useb https://raw.githubusercontent.com/KalimeroMK/kimi-mcp-hub/main/install/install.ps1 | & ([scriptblock]::create($_)) -Yes
#   iwr -useb https://raw.githubusercontent.com/KalimeroMK/kimi-mcp-hub/main/install/install.ps1 | & ([scriptblock]::create($_)) -Yes -WithObsidian

[CmdletBinding()]
param(
    [switch]$Yes,
    [switch]$WithObsidian,
    [string]$ObsidianVault = "$env:USERPROFILE\Documents\Kimi-Memory"
)

$REPO = "KalimeroMK/kimi-mcp-hub"
$INSTALL_DIR = if ($env:KIMI_MCP_HUB_DIR) { $env:KIMI_MCP_HUB_DIR } else { "$env:USERPROFILE\.kimi-mcp-hub" }
$VENV_DIR = "$INSTALL_DIR\.venv"

function Write-Header {
    Write-Host ""
    Write-Host "  KIMI MCP HUB" -ForegroundColor Cyan -NoNewline
    Write-Host " - One-click MCP server & skills manager" -ForegroundColor Gray
    Write-Host "  24 MCP Servers | 57 AI Skills | Persistent Memory" -ForegroundColor DarkGray
    Write-Host ""
}

function Check-Requirements {
    Write-Host "Checking requirements..." -ForegroundColor Cyan
    
    # Check Python (prefer 3.10+)
    $PYTHON = $null
    foreach ($py in @("python3.13", "python3.12", "python3.11", "python3.10", "python", "python3")) {
        if (Get-Command $py -ErrorAction SilentlyContinue) {
            $verStr = (& $py --version 2>&1).ToString()
            if ($verStr -match "Python (\d+)\.(\d+)") {
                $major = [int]$matches[1]
                $minor = [int]$matches[2]
                if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 10)) {
                    $PYTHON = $py
                    $pyVersion = "$major.$minor"
                    break
                }
            }
        }
    }
    
    if (-not $PYTHON) {
        Write-Host "  Python 3.10+ is required. Install from https://python.org/downloads" -ForegroundColor Red
        exit 1
    }
    $script:PYTHON = $PYTHON
    Write-Host "  Python $pyVersion found" -ForegroundColor Green
    
    # Check pip
    if (& $PYTHON -m pip --version -ErrorAction SilentlyContinue) {
        Write-Host "  pip found" -ForegroundColor Green
    } else {
        Write-Host "  pip not found. Run: $PYTHON -m ensurepip --upgrade" -ForegroundColor Red
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

function New-VirtualEnvironment {
    Write-Host "Ensuring isolated Python environment..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Force -Path $INSTALL_DIR | Out-Null
    if (Test-Path $VENV_DIR) {
        Remove-Item -Recurse -Force $VENV_DIR
    }
    & $script:PYTHON -m venv $VENV_DIR
    & "$VENV_DIR\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
    Write-Host "  Virtual environment ready" -ForegroundColor Green
}

function Add-ToPath {
    $venvScripts = "$VENV_DIR\Scripts"
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($currentPath -notlike "*$venvScripts*") {
        [Environment]::SetEnvironmentVariable("Path", "$venvScripts;$currentPath", "User")
        Write-Host "  Added $venvScripts to user PATH" -ForegroundColor Green
        Write-Host "  Restart your terminal for PATH changes to take effect." -ForegroundColor Yellow
    }
    # Also add to current process PATH so the rest of the script can use it
    $env:Path = "$venvScripts;$env:Path"
}

function Install-FromGitHub {
    Write-Host "Installing from GitHub..." -ForegroundColor Cyan
    
    # Remove old install if exists
    if (Test-Path $INSTALL_DIR) {
        Remove-Item -Recurse -Force $INSTALL_DIR
    }
    
    git clone --depth 1 "https://github.com/$REPO.git" $INSTALL_DIR
    Write-Host "  Cloned to $INSTALL_DIR" -ForegroundColor Green
    
    New-VirtualEnvironment
    & "$VENV_DIR\Scripts\pip.exe" install --upgrade -e $INSTALL_DIR
    Add-ToPath
    Write-Host "  Package installed" -ForegroundColor Green
}

function Install-PipGit {
    Write-Host "Installing directly from GitHub (pip)..." -ForegroundColor Cyan
    New-VirtualEnvironment
    & "$VENV_DIR\Scripts\pip.exe" install --upgrade "git+https://github.com/$REPO.git"
    Add-ToPath
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
    if ($WithObsidian) {
        Write-Host "Install with Obsidian local memory:" -ForegroundColor Cyan
        Write-Host "  iwr -useb .../install.ps1 | & ([scriptblock]::create(`$_)) -Yes -WithObsidian"
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

function Setup-ObsidianMcp {
    Write-Host "Setting up Obsidian as local memory..." -ForegroundColor Cyan
    
    if (-not $Yes -and [console]::IsInputRedirected -eq $false) {
        $inputVault = Read-Host "Obsidian vault path [$ObsidianVault]"
        if ($inputVault) { $ObsidianVault = $inputVault }
    }
    
    New-Item -ItemType Directory -Force -Path "$ObsidianVault\.obsidian" | Out-Null

    # obsidian-mcp requires at least app.json to consider this a valid vault
    if (-not (Test-Path "$ObsidianVault\.obsidian\app.json")) {
        '{}' | Set-Content -Path "$ObsidianVault\.obsidian\app.json" -Encoding UTF8
    }

    if (-not (Test-Path "$ObsidianVault\README.md")) {
        @"
# Kimi Memory Vault

This vault is used by Kimi CLI as local memory.

- Notes created by Kimi are stored here.
- Open this folder in Obsidian to browse and edit.
- Source: https://obsidian.md
"@ | Set-Content -Path "$ObsidianVault\README.md" -Encoding UTF8
    }
    
    $mcpJson = "$env:USERPROFILE\.kimi-code\mcp.json"
    New-Item -ItemType Directory -Force -Path (Split-Path $mcpJson) | Out-Null
    $data = @{ mcpServers = @{} }
    if (Test-Path $mcpJson) {
        try {
            $data = Get-Content $mcpJson -Raw | ConvertFrom-Json -AsHashtable
        } catch {
            $data = @{ mcpServers = @{} }
        }
    }
    if (-not $data.ContainsKey("mcpServers")) { $data["mcpServers"] = @{} }
    $data["mcpServers"]["obsidian"] = @{
        command = "npx"
        args = @("-y", "obsidian-mcp", $ObsidianVault)
        env = @{}
    }
    $data | ConvertTo-Json -Depth 10 | Set-Content -Path $mcpJson -Encoding UTF8
    
    Write-Host "  Obsidian vault ready: $ObsidianVault" -ForegroundColor Green
    Write-Host "  Install Obsidian from https://obsidian.md and open this vault." -ForegroundColor Gray
}

# Main
Write-Header
Check-Requirements
Install-PipGit
if ($Yes) {
    Apply-ClaudeCompat
}
if ($WithObsidian) {
    Setup-ObsidianMcp
}
Show-Welcome
