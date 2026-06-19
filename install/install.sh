#!/usr/bin/env bash
# Kimi MCP Hub - One-line installer
# Usage: curl -fsSL https://raw.githubusercontent.com/KalimeroMK/kimi-mcp-hub/main/install/install.sh | bash

set -e

REPO="KalimeroMK/kimi-mcp-hub"
INSTALL_DIR="${KIMI_MCP_HUB_DIR:-$HOME/.kimi-mcp-hub}"
BIN_DIR="${KIMI_MCP_HUB_BIN:-$HOME/.local/bin}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
DIM='\033[0;90m'
NC='\033[0m'

print_header() {
    echo ""
    echo -e "${CYAN}  KIMI MCP HUB${NC} - One-click MCP server & skills manager"
    echo -e "${DIM}  23 MCP Servers | 34 AI Skills | Persistent Memory${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_info() {
    echo -e "${CYAN}→${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

check_requirements() {
    print_info "Checking requirements..."
    
    # Check Python
    if command -v python3 &>/dev/null; then
        PYTHON="python3"
    elif command -v python &>/dev/null; then
        PYTHON="python"
    else
        print_error "Python 3.10+ is required but not found."
        echo "   Install from: https://python.org/downloads"
        exit 1
    fi
    
    PYTHON_VERSION=$($PYTHON --version 2>&1 | cut -d' ' -f2)
    print_success "Python $PYTHON_VERSION found"
    
    # Check pip
    if ! $PYTHON -m pip --version &>/dev/null 2>&1; then
        print_error "pip is required but not found."
        echo "   Install: $PYTHON -m ensurepip --upgrade"
        exit 1
    fi
    print_success "pip found"
    
    # Check Node.js (optional, for MCP servers)
    if command -v node &>/dev/null; then
        NODE_VERSION=$(node --version 2>/dev/null || echo "?")
        print_success "Node.js $NODE_VERSION found (for MCP servers)"
    else
        print_warning "Node.js not found (needed for some MCP servers)"
        echo "   Install from: https://nodejs.org"
    fi
    
    # Check npx (optional)
    if command -v npx &>/dev/null; then
        print_success "npx found"
    else
        print_warning "npx not found (needed for some MCP servers)"
    fi
}

detect_shell() {
    case "$(basename "$SHELL")" in
        bash) echo "bash" ;;
        zsh)  echo "zsh"  ;;
        fish) echo "fish" ;;
        *)    echo "unknown" ;;
    esac
}

add_to_path() {
    local shell_rc=""
    local shell_name=$(detect_shell)
    
    case "$shell_name" in
        bash) shell_rc="$HOME/.bashrc" ;;
        zsh)  shell_rc="$HOME/.zshrc" ;;
        fish) shell_rc="$HOME/.config/fish/config.fish" ;;
        *)    shell_rc="$HOME/.profile" ;;
    esac
    
    # Check if already in PATH
    if [[ ":$PATH:" == *":$BIN_DIR:"* ]]; then
        return 0
    fi
    
    if [ -f "$shell_rc" ]; then
        echo "" >> "$shell_rc"
        echo "# Added by Kimi MCP Hub installer" >> "$shell_rc"
        if [ "$shell_name" = "fish" ]; then
            echo "set -x PATH $BIN_DIR \$PATH" >> "$shell_rc"
        else
            echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$shell_rc"
        fi
        print_info "Added $BIN_DIR to PATH in $shell_rc"
        print_warning "Run: source $shell_rc  (or restart your terminal)"
    fi
}

install_from_pypi() {
    print_info "Installing kimi-mcp-hub from PyPI..."
    $PYTHON -m pip install --upgrade --user kimi-mcp-hub
    print_success "Installed from PyPI"
}

install_from_github() {
    print_info "Cloning repository..."
    
    # Remove old install if exists
    if [ -d "$INSTALL_DIR" ]; then
        rm -rf "$INSTALL_DIR"
    fi
    
    git clone --depth 1 "https://github.com/$REPO.git" "$INSTALL_DIR"
    print_success "Cloned to $INSTALL_DIR"
    
    print_info "Installing package..."
    cd "$INSTALL_DIR"
    $PYTHON -m pip install --upgrade --user -e .
    print_success "Package installed"
}

install_pip_git() {
    print_info "Installing directly from GitHub (pip)..."
    $PYTHON -m pip install --upgrade --user "git+https://github.com/$REPO.git"
    print_success "Installed from GitHub"
}

post_install() {
    print_info "Running post-install setup..."
    
    # Ensure bin directory exists
    mkdir -p "$BIN_DIR"
    
    # Check if kimi-mcp-hub is in PATH
    if ! command -v kimi-mcp-hub &>/dev/null; then
        # Try to find the installed script
        USER_BASE=$($PYTHON -m site --user-base 2>/dev/null || echo "$HOME/.local")
        SCRIPT_DIR="$USER_BASE/bin"
        
        if [ -f "$SCRIPT_DIR/kimi-mcp-hub" ]; then
            print_info "Found kimi-mcp-hub at $SCRIPT_DIR"
            add_to_path
        fi
    fi
    
    # Create ~/.kimi directory
    mkdir -p "$HOME/.kimi"
    
    print_success "Setup complete"
}

show_welcome() {
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║${NC}  ${CYAN}Kimi MCP Hub${NC} installed successfully!                ${GREEN}║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}Quick start:${NC}"
    echo "  kimi-mcp-hub init      # Run interactive setup wizard"
    echo "  kimi-mcp-hub status    # Check installation status"
    echo "  kimi-mcp-hub welcome   # Show welcome banner"
    echo "  kimi-mcp-hub doctor    # Check system health"
    echo ""
    echo -e "${CYAN}Add your first server:${NC}"
    echo "  kimi-mcp-hub add github"
    echo "  kimi-mcp-hub auth github  # Auto-browser OAuth"
    echo ""
    echo -e "${CYAN}Use in Kimi CLI:${NC}"
    echo "  /mcp       # List available tools"
    echo "  /skills    # List installed skills"
    echo ""
    echo -e "${DIM}Need help? Run: kimi-mcp-hub --help${NC}"
    echo ""
}

main() {
    print_header
    check_requirements
    
    # Parse arguments
    METHOD="${1:-auto}"
    
    case "$METHOD" in
        --pip|pip)
            install_pip_git
            ;;
        --clone|clone)
            install_from_github
            ;;
        --pypi|pypi)
            install_from_pypi
            ;;
        *)
            # Try PyPI first, fallback to pip+git
            if $PYTHON -m pip install --dry-run kimi-mcp-hub &>/dev/null 2>&1; then
                install_from_pypi
            else
                print_info "PyPI package not found, installing from GitHub..."
                install_pip_git
            fi
            ;;
    esac
    
    post_install
    show_welcome
}

main "$@"
