"""Obsidian MCP server configuration."""

import json
import re
import shutil
from pathlib import Path
from typing import Any


class ObsidianServer:
    """Obsidian vault MCP server -- local memory as markdown files.

    Uses obsidian-mcp v2 (file-based, no Obsidian plugin required).
    Obsidian itself is only needed if you want to view/edit the vault
    through the desktop app.

    Supports a single vault or multiple vaults. Each vault is registered
    under a slug id (``--vault slug=/abs/path``) and obsidian-mcp tools
    take that id as their ``vault`` parameter.
    """

    name = "obsidian"
    display_name = "Obsidian"
    description = "Read and write your Obsidian vault as local memory. No Obsidian plugin required; just point it at a vault folder."
    icon = "🧠"

    @classmethod
    def get_stdio_config(cls, vault_path: str | list[str]) -> dict[str, Any]:
        """Return stdio config for one or more vault paths.

        obsidian-mcp v2 requires the explicit ``serve`` subcommand and one
        ``--vault <slug>=<path>`` flag per vault.
        """
        paths = [vault_path] if isinstance(vault_path, str) else vault_path
        args = ["-y", "obsidian-mcp@2", "serve"]
        for path in paths:
            args += ["--vault", f"{cls.slug_from_vault_path(path)}={path}"]
        return {
            "command": "npx",
            "args": args,
            "env": {},
        }

    @classmethod
    def get_tools(cls) -> list[dict[str, str]]:
        # Tool names verified against obsidian-mcp@2 `tools/list`.
        return [
            {"name": "obsidian_list_vaults", "desc": "List configured vault ids"},
            {"name": "obsidian_read_note", "desc": "Read a note (paginated, with etag)"},
            {"name": "obsidian_create_note", "desc": "Create a note without overwriting"},
            {"name": "obsidian_edit_note", "desc": "Append, prepend, or replace note content"},
            {"name": "obsidian_delete_note", "desc": "Move a note to trash or delete it"},
            {"name": "obsidian_move_note", "desc": "Move or rename a note and update backlinks"},
            {"name": "obsidian_create_directory", "desc": "Create a directory inside a vault"},
            {"name": "obsidian_search_vault", "desc": "Search content, filenames, or tags"},
            {"name": "obsidian_add_tags", "desc": "Add tags to one or more notes"},
            {"name": "obsidian_remove_tags", "desc": "Remove tags from notes"},
            {"name": "obsidian_rename_tag", "desc": "Rename a tag across the vault"},
            {"name": "obsidian_manage_tags", "desc": "Unified add/remove tag workflow"},
        ]

    @classmethod
    def slug_from_vault_path(cls, vault_path: str | Path) -> str:
        """Generate a safe slug from a vault path.

        The slug is derived from the directory name, lower-cased, and stripped
        of characters that are risky in MCP args or identifiers. obsidian-mcp
        vault ids must begin with a letter, so a leading digit or dash gets a
        ``v-`` prefix.
        """
        name = Path(vault_path).name
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        if not slug:
            return "vault"
        if not slug[0].isalpha():
            slug = f"v-{slug}"
        return slug

    @classmethod
    def validate_vault(cls, vault_path: str | Path, fix: bool = False) -> bool:
        """Return True if ``vault_path`` looks like an Obsidian vault.

        A vault is considered valid when it contains a ``.obsidian`` directory
        and a ``.obsidian/app.json`` file. If ``fix`` is True, missing items
        are created so obsidian-mcp can use the folder without opening Obsidian.

        If ``fix`` is True and the required directories or app.json cannot be
        created (for example, because the path points to an existing file),
        returns False instead of raising.
        """
        path = Path(vault_path)
        obsidian_dir = path / ".obsidian"
        app_json = obsidian_dir / "app.json"

        if fix:
            try:
                path.mkdir(parents=True, exist_ok=True)
                obsidian_dir.mkdir(exist_ok=True)
                if not app_json.exists():
                    cls._write_app_json(app_json)
            except OSError:
                return False

        return obsidian_dir.is_dir() and app_json.is_file()

    @classmethod
    def scaffold_vault(cls, vault_path: Path) -> None:
        """Create a minimal vault structure."""
        vault_path.mkdir(parents=True, exist_ok=True)
        cls.validate_vault(vault_path, fix=True)
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

    @classmethod
    def sync_templates(
        cls,
        templates_dir: Path,
        vault_path: Path,
        *,
        overwrite: bool = False,
        missing_ok: bool = False,
    ) -> list[Path]:
        """Copy template notes from ``templates_dir`` into ``vault_path``.

        Only ``.md`` files are copied, preserving the relative directory
        structure. Hidden files and directories are ignored. Returns the list
        of destination paths that were written.

        By default ``overwrite`` is False, so existing notes in the vault are
        left untouched. Set ``overwrite=True`` to replace them with templates.

        If ``templates_dir`` does not exist and ``missing_ok`` is False, a
        ``FileNotFoundError`` is raised. When ``missing_ok`` is True, a missing
        directory is treated as an empty template set and an empty list is
        returned.
        """
        copied: list[Path] = []
        templates_dir = Path(templates_dir)
        vault_path = Path(vault_path)
        if not templates_dir.exists():
            if missing_ok:
                return copied
            raise FileNotFoundError(f"Templates directory not found: {templates_dir}")

        for source in templates_dir.rglob("*.md"):
            if any(
                part.startswith(".") for part in source.relative_to(templates_dir).parts
            ):
                continue
            relative = source.relative_to(templates_dir)
            destination = vault_path / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if overwrite or not destination.exists():
                shutil.copy2(source, destination)
                copied.append(destination)

        return copied

    @classmethod
    def _write_app_json(cls, app_json: Path) -> None:
        """Write a minimal ``app.json`` so obsidian-mcp recognizes the vault."""
        app_json.write_text(
            json.dumps(
                {"newFileLocation": "folder", "newFileFolderPath": ""}, indent=2
            ),
            encoding="utf-8",
        )
