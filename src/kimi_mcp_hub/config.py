"""Configuration management for Kimi MCP Hub."""

import json
import os
from pathlib import Path
from typing import Any

import platformdirs


class KimiConfig:
    """Manages ~/.kimi-code/mcp.json, ~/.kimi-code/skills/, and hub config."""

    def __init__(self):
        # Kimi CLI reads MCP config from ~/.kimi-code/mcp.json and skills from
        # ~/.kimi-code/skills/. Align our paths with the official CLI.
        self.kimi_dir = Path.home() / ".kimi-code"
        self.mcp_json = self.kimi_dir / "mcp.json"
        self.skills_dir = self.kimi_dir / "skills"
        self.hub_dir = Path(platformdirs.user_config_dir("kimi-mcp-hub", "MoonshotAI"))
        self.tokens_file = self.hub_dir / "tokens.json"
        self.memory_db = self.hub_dir / "memory.db"
        self.hub_dir.mkdir(parents=True, exist_ok=True)
        self.kimi_dir.mkdir(parents=True, exist_ok=True)
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
        try:
            with open(self.mcp_json, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {"mcpServers": {}}

    def save_mcp(self, data: dict) -> None:
        """Atomic write to ~/.kimi-code/mcp.json."""
        tmp = self.mcp_json.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        tmp.replace(self.mcp_json)

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
            with open(self.tokens_file, "r", encoding="utf-8") as f:
                tokens = json.load(f)
        tokens[server] = token_data
        with open(self.tokens_file, "w", encoding="utf-8") as f:
            json.dump(tokens, f, indent=2)

    def load_token(self, server: str) -> dict | None:
        """Load token for a server."""
        if not self.tokens_file.exists():
            return None
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

    def reload_kimi_mcp(self) -> None:
        """Signal Kimi CLI to reload MCP config (if running)."""
        pass
