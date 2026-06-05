"""Kimi MCP Hub -- One-click MCP server and skills manager for Kimi CLI."""

__version__ = "0.1.0"
__title__ = "Kimi MCP Hub"
__description__ = "One-click MCP server and skills manager for Kimi CLI"
__author__ = "KalimeroMK"

# Total counts for display
TOTAL_SERVERS = 17
TOTAL_SKILLS = 28

from .config import KimiConfig

# Lazy imports to avoid circular dependencies
__all__ = ["__version__", "__title__", "KimiConfig"]

# Show welcome message on first import (e.g., when CLI starts)
try:
    from ._post_install import check_first_run
    check_first_run()
except Exception:
    pass  # Silently ignore if anything goes wrong
