"""Named configuration profiles.

A profile is a named snapshot of the global ``mcpServers`` config, stored as
JSON in ``<config-dir>/kimi-mcp-hub/profiles/<name>.json``. Profiles let you
switch the whole server set at once (e.g. "work" vs "personal") independent
of per-project configs.
"""

from __future__ import annotations

import json
from pathlib import Path

import platformdirs


class ProfileStore:
    """Manages named MCP-server bundles on disk."""

    def __init__(self, profiles_dir: Path | None = None):
        if profiles_dir is None:
            hub_dir = Path(platformdirs.user_config_dir("kimi-mcp-hub", "MoonshotAI"))
            profiles_dir = hub_dir / "profiles"
        self.dir = profiles_dir

    def _path(self, name: str) -> Path:
        if not name or "/" in name or "\\" in name or name.startswith("."):
            raise ValueError(f"Invalid profile name: {name!r}")
        return self.dir / f"{name}.json"

    def list(self) -> list[str]:
        """Return profile names, sorted."""
        if not self.dir.exists():
            return []
        return sorted(p.stem for p in self.dir.glob("*.json"))

    def exists(self, name: str) -> bool:
        return self._path(name).exists()

    def save(self, name: str, mcp_data: dict) -> Path:
        """Store an MCP config snapshot under ``name``."""
        path = self._path(name)
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(mcp_data, f, indent=2, ensure_ascii=False)
        tmp.replace(path)
        return path

    def load(self, name: str) -> dict | None:
        """Return the stored config, or None if the profile does not exist."""
        path = self._path(name)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None

    def remove(self, name: str) -> bool:
        """Delete a profile. Returns True if it existed."""
        path = self._path(name)
        if not path.exists():
            return False
        path.unlink()
        return True
