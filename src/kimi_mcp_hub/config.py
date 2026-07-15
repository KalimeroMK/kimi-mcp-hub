"""Configuration management for Kimi MCP Hub."""

import json
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
        # Directories are created lazily by the write paths (_secure_write,
        # save_toml_config, install_skill, plugin_dir, ...), so instantiating
        # KimiConfig for a read-only command has no filesystem side effects.
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

    # --- Obsidian helpers ---

    def get_obsidian_vaults(self) -> list[str]:
        """Return configured Obsidian vault paths from mcp.json."""
        obsidian = self.load_mcp().get("mcpServers", {}).get("obsidian", {})
        args = obsidian.get("args", [])
        if len(args) >= 2 and args[0] == "-y" and args[1] == "obsidian-mcp":
            return list(args[2:])
        return []

    def set_obsidian_vaults(self, vaults: list[str]) -> None:
        """Update or remove the obsidian server entry in mcp.json."""
        data = self.load_mcp()
        data.setdefault("mcpServers", {})
        if vaults:
            data["mcpServers"]["obsidian"] = {
                "command": "npx",
                "args": ["-y", "obsidian-mcp", *vaults],
                "env": {},
            }
        else:
            data["mcpServers"].pop("obsidian", None)
        self.save_mcp(data)

    def get_default_memory_vault(self) -> str | None:
        """Return the default memory vault path from config.toml, if set."""
        return self.load_toml_config().get("memory", {}).get("default_vault")

    def set_default_memory_vault(self, vault_path: str) -> None:
        """Store the default memory vault path in config.toml."""
        data = self.load_toml_config()
        data.setdefault("memory", {})["default_vault"] = vault_path
        self.save_toml_config(data)

    def clear_default_memory_vault(self) -> None:
        """Remove the default memory vault path from config.toml."""
        data = self.load_toml_config()
        data.get("memory", {}).pop("default_vault", None)
        if not data.get("memory"):
            data.pop("memory", None)
        self.save_toml_config(data)

    # --- Memory summary helpers ---

    def get_memory_summary_api_key(self) -> str:
        """Return the memory summary API key from config.toml, if set."""
        return self.load_toml_config().get("memory", {}).get("summary_api_key", "")

    def get_memory_summary_model(self) -> str:
        """Return the memory summary model from config.toml."""
        return self.load_toml_config().get("memory", {}).get("summary_model", "gpt-4o-mini")

    def get_memory_summary_base_url(self) -> str:
        """Return the memory summary base URL from config.toml."""
        return self.load_toml_config().get("memory", {}).get(
            "summary_base_url", "https://api.openai.com/v1"
        )

    def is_memory_summary_enabled(self) -> bool:
        """Return whether memory summarization is enabled.

        If summary_enabled is explicitly set, that value wins. Otherwise,
        summarization is enabled when a summary_api_key is configured.
        """
        memory = self.load_toml_config().get("memory", {})
        if "summary_enabled" in memory:
            return bool(memory["summary_enabled"])
        return bool(memory.get("summary_api_key", ""))

    def set_memory_summary_config(
        self,
        api_key: str = "",
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        enabled: bool = True,
    ) -> None:
        """Store memory summarization settings in config.toml.

        This overwrites all memory summary keys in config.toml with the
        provided values.
        """
        data = self.load_toml_config()
        memory = data.setdefault("memory", {})
        memory["summary_api_key"] = api_key
        memory["summary_model"] = model
        memory["summary_base_url"] = base_url
        memory["summary_enabled"] = enabled
        self.save_toml_config(data)

    def _load_tokens(self) -> dict:
        """Load the tokens file, tolerating corruption."""
        if not self.tokens_file.exists():
            return {}
        self._warn_if_readable_by_others(self.tokens_file)
        try:
            with open(self.tokens_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
        return data if isinstance(data, dict) else {}

    def save_token(self, server: str, token_data: dict) -> None:
        """Save OAuth/token data securely."""
        tokens = self._load_tokens()
        tokens[server] = token_data
        self._secure_write(self.tokens_file, tokens)

    def load_token(self, server: str) -> dict | None:
        """Load token for a server."""
        return self._load_tokens().get(server)

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

    def remove_agents_md_section(self, marker: str) -> bool:
        """Remove a plugin's marked section from ~/.kimi-code/AGENTS.md.

        Returns True if the file was changed, False if the marker was not found.
        """
        import re

        start_marker = f"<!-- plugin: {marker} -->"
        end_marker = f"<!-- /plugin: {marker} -->"

        if not self.agents_md.exists():
            return False

        existing = self.agents_md.read_text(encoding="utf-8")
        if start_marker not in existing:
            return False

        pattern = re.escape(start_marker) + r".*?" + re.escape(end_marker)
        new_text = re.sub(pattern, "", existing, count=1, flags=re.DOTALL)
        new_text = new_text.strip()
        if new_text:
            self.agents_md.write_text(new_text + "\n", encoding="utf-8")
        else:
            self.agents_md.unlink()
        return True
