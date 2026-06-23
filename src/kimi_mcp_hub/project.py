"""Project-level MCP configuration support.

Each project can keep its own `.kimi/mcp.json` and `.kimi/mcp.env`.
`kimi-mcp-hub sync` merges the project config on top of the global
`~/.kimi/mcp.json` so Kimi CLI sees project-specific servers.
"""

from __future__ import annotations

import copy
import json
import os
import re
from pathlib import Path


PLACEHOLDER_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def find_project_root(start_dir: str | Path | None = None) -> Path | None:
    """Locate the nearest project root.

    Prefers a directory that contains `.kimi/`, then falls back to a git root.
    Walks upward from ``start_dir`` (or ``os.getcwd()``) until ``/``.
    """
    cwd = Path(start_dir or os.getcwd()).resolve()
    for path in [cwd, *cwd.parents]:
        if (path / ".kimi").is_dir():
            return path
        if (path / ".git").exists():
            return path
    return None


def resolve_placeholders(obj, env: dict) -> object:
    """Recursively replace ${VAR} placeholders with values from ``env``."""
    if isinstance(obj, str):

        def _replace(match: re.Match) -> str:
            return env.get(match.group(1), match.group(0))

        return PLACEHOLDER_RE.sub(_replace, obj)
    if isinstance(obj, dict):
        return {k: resolve_placeholders(v, env) for k, v in obj.items()}
    if isinstance(obj, list):
        return [resolve_placeholders(v, env) for v in obj]
    return obj


def merge_mcp_configs(base: dict, overlay: dict) -> dict:
    """Merge two MCP configs, with overlay taking precedence for server names."""
    merged = {"mcpServers": {}}
    merged["mcpServers"].update(base.get("mcpServers", {}))
    merged["mcpServers"].update(overlay.get("mcpServers", {}))
    return merged


class ProjectConfig:
    """Manages ``<project>/.kimi/mcp.json`` and ``<project>/.kimi/mcp.env``."""

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.kimi_dir = self.root / ".kimi"
        self.mcp_json = self.kimi_dir / "mcp.json"
        self.env_file = self.kimi_dir / "mcp.env"

    def exists(self) -> bool:
        return self.mcp_json.exists()

    def ensure_dir(self) -> None:
        self.kimi_dir.mkdir(parents=True, exist_ok=True)

    def load_mcp(self) -> dict:
        if not self.mcp_json.exists():
            return {"mcpServers": {}}
        try:
            with open(self.mcp_json, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {"mcpServers": {}}

    def save_mcp(self, data: dict) -> None:
        self.ensure_dir()
        tmp = self.mcp_json.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        tmp.replace(self.mcp_json)

    def add_server(self, name: str, cfg: dict) -> dict:
        """Add or update a server in the project config.

        Secret env values are extracted to ``.kimi/mcp.env`` and replaced with
        ``${VAR}`` placeholders in ``.kimi/mcp.json``.
        """
        cfg_with_placeholders, env_updates = self._extract_env_vars(cfg)
        data = self.load_mcp()
        data.setdefault("mcpServers", {})
        data["mcpServers"][name] = cfg_with_placeholders
        self.save_mcp(data)
        if env_updates:
            self._update_env_file(env_updates)
        return cfg_with_placeholders

    def remove_server(self, name: str) -> None:
        data = self.load_mcp()
        data.setdefault("mcpServers", {})
        data["mcpServers"].pop(name, None)
        self.save_mcp(data)

    def load_env(self) -> dict[str, str]:
        """Return merged environment: shell env overridden by ``.kimi/mcp.env``."""
        env = dict(os.environ)
        if self.env_file.exists():
            with open(self.env_file, "r", encoding="utf-8") as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    env[key.strip()] = value.strip()
        return env

    def _extract_env_vars(self, cfg: dict) -> tuple[dict, dict[str, str]]:
        """Replace env values with placeholders and collect them for .mcp.env."""
        cfg = copy.deepcopy(cfg)
        env_updates: dict[str, str] = {}
        env = cfg.get("env", {})
        if isinstance(env, dict):
            for key, value in list(env.items()):
                if isinstance(value, str) and not PLACEHOLDER_RE.fullmatch(value):
                    env_updates[key] = value
                    env[key] = f"${{{key}}}"
        return cfg, env_updates

    def _update_env_file(self, updates: dict[str, str]) -> None:
        self.ensure_dir()
        existing: dict[str, str] = {}
        if self.env_file.exists():
            with open(self.env_file, "r", encoding="utf-8") as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    existing[key.strip()] = value.strip()
        existing.update(updates)
        with open(self.env_file, "w", encoding="utf-8") as f:
            f.write("# Kimi MCP Hub project environment variables\n")
            f.write("# This file should be added to .gitignore\n\n")
            for key in sorted(existing):
                f.write(f"{key}={existing[key]}\n")
