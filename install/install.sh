#!/usr/bin/env bash
# Kimi MCP Hub - One-line installer
# Usage: curl -fsSL https://raw.githubusercontent.com/KalimeroMK/kimi-mcp-hub/main/install/install.sh | bash
# Usage with Obsidian: curl -fsSL .../install.sh | bash -s -- --with-obsidian

set -e

REPO="KalimeroMK/kimi-mcp-hub"
INSTALL_DIR="${KIMI_MCP_HUB_DIR:-$HOME/.kimi-mcp-hub}"
VENV_DIR="$INSTALL_DIR/.venv"
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
    echo -e "${DIM}  24 MCP Servers | 57 AI Skills | Persistent Memory${NC}"
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
    
    # Check Python (prefer 3.10+ specifically)
    PYTHON=""
    for py in python3.13 python3.12 python3.11 python3.10 python3 python; do
        if command -v "$py" &>/dev/null; then
            ver=$($py --version 2>&1 | cut -d' ' -f2)
            major=$(echo "$ver" | cut -d'.' -f1)
            minor=$(echo "$ver" | cut -d'.' -f2)
            if [ "$major" -gt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -ge 10 ]; }; then
                PYTHON="$py"
                PYTHON_VERSION="$ver"
                break
            fi
        fi
    done
    
    if [ -z "$PYTHON" ]; then
        print_error "Python 3.10+ is required but not found."
        echo "   Install from: https://python.org/downloads"
        exit 1
    fi
    
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

create_venv() {
    print_info "Ensuring isolated Python environment..."
    mkdir -p "$INSTALL_DIR"
    if [ ! -d "$VENV_DIR/bin" ]; then
        $PYTHON -m venv "$VENV_DIR"
    fi
    "$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel
    print_success "Virtual environment ready"
}

link_binaries() {
    mkdir -p "$BIN_DIR"
    if [ -f "$VENV_DIR/bin/kimi-mcp-hub" ]; then
        ln -sf "$VENV_DIR/bin/kimi-mcp-hub" "$BIN_DIR/kimi-mcp-hub"
    fi
    if [ -f "$VENV_DIR/bin/kmcp" ]; then
        ln -sf "$VENV_DIR/bin/kmcp" "$BIN_DIR/kmcp"
    fi
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
    create_venv
    "$VENV_DIR/bin/pip" install --upgrade -e "$INSTALL_DIR"
    link_binaries
    print_success "Package installed"
}

install_pip_git() {
    print_info "Installing directly from GitHub (pip)..."
    create_venv
    "$VENV_DIR/bin/pip" install --upgrade "git+https://github.com/$REPO.git"
    link_binaries
    print_success "Installed from GitHub"
}

post_install() {
    print_info "Running post-install setup..."
    
    # Ensure binaries are linked
    link_binaries
    
    # Check if kimi-mcp-hub is in PATH
    if ! command -v kimi-mcp-hub &>/dev/null; then
        if [ -f "$BIN_DIR/kimi-mcp-hub" ]; then
            print_info "Found kimi-mcp-hub at $BIN_DIR"
            add_to_path
        fi
    fi
    
    # Create ~/.kimi directory
    mkdir -p "$HOME/.kimi"
    
    print_success "Setup complete"
}

setup_obsidian_mcp() {
    print_info "Setting up Obsidian as local memory..."

    local vault_path="${OBSIDIAN_VAULT:-}"

    if [ -z "$vault_path" ] && [ "$AUTO_YES" = false ] && [ -t 0 ]; then
        read -rp "Obsidian vault path (empty = standard location for this OS): " input
        vault_path="$input"
    fi

    # The CLI owns the default location, the vault layout, the mcp.json shape,
    # and registering the vault as the default memory vault. Passing no path
    # lets it pick the right place for this OS: <Documents>/Kimi-Memory, or
    # ~/Kimi-Memory on a machine with no Documents folder. Hardcoding a path
    # here would land in an English "Documents" beside the real, localized one
    # on a non-English Linux desktop.
    if [ -n "$vault_path" ]; then
        vault_path="$(eval echo "$vault_path")"
        "$VENV_DIR/bin/kimi-mcp-hub" obsidian add "$vault_path" || {
            print_error "Could not configure the Obsidian vault at $vault_path"
            return 1
        }
    else
        "$VENV_DIR/bin/kimi-mcp-hub" obsidian add || {
            print_error "Could not configure the Obsidian vault"
            return 1
        }
    fi

    print_info "Install Obsidian from https://obsidian.md and open that vault."
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
    echo -e "${CYAN}Install with auto CLAUDE.md support:${NC}"
    echo "  curl -fsSL .../install.sh | bash -s -- -y"
    echo ""
    echo -e "${CYAN}Install with Obsidian local memory:${NC}"
    echo "  curl -fsSL .../install.sh | bash -s -- --with-obsidian"
    echo ""
    echo -e "${DIM}Need help? Run: kimi-mcp-hub --help${NC}"
    echo ""
}

main() {
    print_header
    check_requirements
    
    # Parse arguments
    AUTO_YES=false
    WITH_OBSIDIAN=false
    OBSIDIAN_VAULT=""
    METHOD="auto"
    
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -y|--yes)
                AUTO_YES=true
                shift
                ;;
            --with-obsidian)
                WITH_OBSIDIAN=true
                shift
                ;;
            --obsidian-vault)
                OBSIDIAN_VAULT="$2"
                shift 2
                ;;
            --pip|--clone|pip|clone)
                METHOD="$1"
                shift
                ;;
            *)
                print_warning "Unknown argument: $1"
                shift
                ;;
        esac
    done
    
    case "$METHOD" in
        --pip|pip)
            install_pip_git
            ;;
        --clone|clone)
            install_from_github
            ;;
        *)
            install_pip_git
            ;;
    esac
    
    post_install
    
    # Auto-apply claude-compat patch when -y is passed
    if [ "$AUTO_YES" = true ]; then
        if command -v kimi-mcp-hub &>/dev/null; then
            print_info "Applying claude-compat patch (auto-load CLAUDE.md and CLAUDE.local.md)..."
            kimi-mcp-hub claude-compat --yes
        else
            print_warning "kimi-mcp-hub not found in PATH. Skipping claude-compat patch."
            print_info "Run manually after adding it to PATH: kimi-mcp-hub claude-compat --yes"
        fi
    fi
    
    # Setup Obsidian MCP server
    if [ "$WITH_OBSIDIAN" = true ]; then
        OBSIDIAN_VAULT="$OBSIDIAN_VAULT" setup_obsidian_mcp
    fi
    
    show_welcome
}

main "$@"
