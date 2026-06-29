"""Kimi MCP Hub -- One-click MCP server and skills manager for Kimi CLI."""

__version__ = "0.1.0"
__title__ = "Kimi MCP Hub"
__description__ = "One-click MCP server and skills manager for Kimi CLI"
__author__ = "KalimeroMK"

# Total counts for display (kept in sync with cli.py SERVERS and SKILLS)
TOTAL_SERVERS = 23
TOTAL_SKILLS = 57

from .config import KimiConfig

# Lazy imports to avoid circular dependencies
__all__ = ["__version__", "__title__", "TOTAL_SERVERS", "TOTAL_SKILLS", "KimiConfig"]
