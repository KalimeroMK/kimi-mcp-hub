"""Kimi MCP Hub -- One-click MCP server and skills manager for Kimi CLI."""

__version__ = "0.3.0"
__title__ = "Kimi MCP Hub"
__description__ = "One-click MCP server and skills manager for Kimi CLI"
__author__ = "KalimeroMK"

from .config import KimiConfig

__all__ = ["__version__", "__title__", "TOTAL_SERVERS", "TOTAL_SKILLS", "KimiConfig"]


def __getattr__(name: str):
    """Lazily derive catalog counts from the registry (single source of truth).

    Kept lazy so importing ``kimi_mcp_hub`` (e.g. in the memory hooks, which
    run on every tool call) does not pay for importing all server modules.
    """
    if name in ("TOTAL_SERVERS", "TOTAL_SKILLS"):
        from .registry import SERVERS, SKILLS

        return len(SERVERS) if name == "TOTAL_SERVERS" else len(SKILLS)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
