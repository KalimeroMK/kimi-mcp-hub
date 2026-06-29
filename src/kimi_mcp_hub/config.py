"""Configuration management for Kimi MCP Hub."""

import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

import platformdirs
import tomli_w

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib


class KimiConfig:
    """Manages ~/.kimi-code/mcp.json, ~/.kimi-code/skills/, and hub config."""

    def __init__(self):
        # Kimi CLI reads MCP config from ~/.kimi-code/mcp.json and skills from
        # ~/.kimi-code/skills/. Align our paths with the official CLI.
        self.kimi_dir = Path.home() / ".kimi-code"
        self.mcp_json = self.kimi_dir / "mcp.json"
        self.skills_dir = self.kimi_dir / "skills"
        self.config_toml = self.kimi_dir / "config.toml"
        self.agents_md = self.kimi_dir / "AGENTS.md"
        self.hub_dir = Path(platformdirs.user_config_dir("kimi-mcp-hub", "MoonshotAI"))
        self.tokens_file = self.hub_dir / "tokens.json"
        self.memory_db = self.hub_dir / "memory.db"
        self.plugins_dir = self.hub_dir / "plugins"
        self.hub_dir.mkdir(parents=True, exist_ok=True)
        self.kimi_dir.mkdir(parents=True, exist_ok=True)
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        # Migrate legacy config from ~/.kimi/mcp.json if the new path is empty
        self._migrate_legacy_config()

    def _migrate_legacy_config(self) -> None:
        """Copy old ~/.kimi/mcp.json to ~/.kimi-code/mcp.json if needed."""
        legacy = Path.home() / ".kimi" / "mcp.json"
        if legacy.exists() and not self.mcp_json.exists():
            try:
                with open(legacy, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.save_mcp(data)
            except (json.JSONDecodeError, OSError):
                pass

    def load_mcp(self) -> dict:
        """Load current ~/.kimi-code/mcp.json."""
        if not self.mcp_json.exists():
            return {"mcpServers": {}}
        self._warn_if_readable_by_others(self.mcp_json)
        try:
            with open(self.mcp_json, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {"mcpServers": {}}

    def _secure_write(self, path: Path, data: dict) -> None:
        """Atomic JSON write with restrictive permissions on Unix."""
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        tmp.replace(path)
        if sys.platform != "win32":
            try:
                path.chmod(0o600)
            except OSError:
                pass

    def _warn_if_readable_by_others(self, path: Path) -> None:
        """Warn if a sensitive file is readable by group or others."""
        if sys.platform == "win32" or not path.exists():
            return
        try:
            mode = path.stat().st_mode
            if mode & stat.S_IRWXG or mode & stat.S_IRWXO:
                print(
                    f"Warning: {path} is readable by group/others. "
                    "Run 'kimi-mcp-hub doctor' to fix permissions."
                )
        except OSError:
            pass

    def save_mcp(self, data: dict) -> None:
        """Atomic write to ~/.kimi-code/mcp.json."""
        self._secure_write(self.mcp_json, data)

    def add_server(self, name: str, config: dict) -> None:
        """Add or update an MCP server."""
        data = self.load_mcp()
        data.setdefault("mcpServers", {})
        data["mcpServers"][name] = config
        self.save_mcp(data)

    def remove_server(self, name: str) -> None:
        """Remove an MCP server."""
        data = self.load_mcp()
        data.setdefault("mcpServers", {})
        data["mcpServers"].pop(name, None)
        self.save_mcp(data)

    def list_servers(self) -> dict[str, dict]:
        """Return dict of {name: config}."""
        return self.load_mcp().get("mcpServers", {})

    def save_token(self, server: str, token_data: dict) -> None:
        """Save OAuth/token data securely."""
        tokens = {}
        if self.tokens_file.exists():
            self._warn_if_readable_by_others(self.tokens_file)
            with open(self.tokens_file, "r", encoding="utf-8") as f:
                tokens = json.load(f)
        tokens[server] = token_data
        self._secure_write(self.tokens_file, tokens)

    def load_token(self, server: str) -> dict | None:
        """Load token for a server."""
        if not self.tokens_file.exists():
            return None
        self._warn_if_readable_by_others(self.tokens_file)
        with open(self.tokens_file, "r", encoding="utf-8") as f:
            tokens = json.load(f)
        return tokens.get(server)

    def install_skill(self, name: str, content: str) -> Path:
        """Install a SKILL.md into ~/.kimi-code/skills/."""
        skill_dir = self.skills_dir / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_file = skill_dir / "SKILL.md"
        with open(skill_file, "w", encoding="utf-8") as f:
            f.write(content)
        return skill_file

    def plugin_dir(self, name: str) -> Path:
        """Return the installation directory for a plugin."""
        path = self.plugins_dir / name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def load_toml_config(self) -> dict[str, Any]:
        """Load ~/.kimi-code/config.toml, returning an empty dict if missing."""
        if not self.config_toml.exists():
            return {}
        try:
            with open(self.config_toml, "rb") as f:
                return tomllib.load(f)
        except (OSError, tomllib.TOMLDecodeError):
            return {}

    def save_toml_config(self, data: dict[str, Any]) -> None:
        """Atomically write ~/.kimi-code/config.toml."""
        self.config_toml.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.config_toml.with_suffix(".tmp")
        with open(tmp, "wb") as f:
            tomli_w.dump(data, f)
        tmp.replace(self.config_toml)
        if sys.platform != "win32":
            try:
                self.config_toml.chmod(0o600)
            except OSError:
                pass

    def merge_agents_md(self, content: str, marker: str) -> bool:
        """Merge plugin AGENTS.md content into ~/.kimi-code/AGENTS.md.

        Uses <!-- plugin: marker --> markers to make reinstalls idempotent.
        Returns True if the file was changed, False if the marker already exists.
        """
        start_marker = f"<!-- plugin: {marker} -->"
        end_marker = f"<!-- /plugin: {marker} -->"
        block = f"\n{start_marker}\n{content.rstrip()}\n{end_marker}\n"

        existing = ""
        if self.agents_md.exists():
            existing = self.agents_md.read_text(encoding="utf-8")

        if start_marker in existing:
            # Replace existing block
            import re
            pattern = re.escape(start_marker) + ".*?" + re.escape(end_marker)
            new_text = re.sub(pattern, block.strip(), existing, flags=re.DOTALL)
            if new_text == existing:
                return False
            self.agents_md.write_text(new_text, encoding="utf-8")
            return True

        self.agents_md.parent.mkdir(parents=True, exist_ok=True)
        with open(self.agents_md, "a", encoding="utf-8") as f:
            f.write(block)
        return True

    def reload_kimi_mcp(self) -> None:
        """Signal Kimi CLI to reload MCP config (if running)."""
        pass
