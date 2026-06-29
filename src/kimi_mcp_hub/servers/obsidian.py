"""Obsidian MCP server configuration."""

from pathlib import Path
from typing import Any


class ObsidianServer:
    """Obsidian vault MCP server — local memory as markdown files.

    Uses obsidian-mcp (file-based, no Obsidian plugin required).
    Obsidian itself is only needed if you want to view/edit the vault
    through the desktop app.
    """

    name = "obsidian"
    display_name = "Obsidian"
    description = "Read and write your Obsidian vault as local memory. No Obsidian plugin required; just point it at a vault folder."
    icon = "🧠"

    @classmethod
    def get_stdio_config(cls, vault_path: str) -> dict[str, Any]:
        return {
            "command": "npx",
            "args": ["-y", "obsidian-mcp", vault_path],
            "env": {}
        }

    @classmethod
    def get_tools(cls) -> list[dict[str, str]]:
        return [
            {"name": "obsidian_read", "desc": "Read a note from the vault"},
            {"name": "obsidian_search", "desc": "Search notes by filename/content"},
            {"name": "obsidian_write", "desc": "Create or update a note"},
            {"name": "obsidian_list", "desc": "List notes in the vault"},
        ]

    @classmethod
    def scaffold_vault(cls, vault_path: Path) -> None:
        """Create a minimal vault structure."""
        vault_path.mkdir(parents=True, exist_ok=True)
        (vault_path / ".obsidian").mkdir(exist_ok=True)
        readme = vault_path / "README.md"
        if not readme.exists():
            readme.write_text(
                "# Kimi Memory Vault\n\n"
                "This vault is used by Kimi CLI as local memory.\n\n"
                "- Notes created by Kimi are stored here.\n"
                "- Open this folder in Obsidian to browse and edit.\n"
                "- Source: https://obsidian.md\n",
                encoding="utf-8",
            )
