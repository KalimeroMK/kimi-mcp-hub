"""Kimi CLI hooks for automatic memory capture."""

from datetime import datetime, timezone
from pathlib import Path

from ..config import KimiConfig
from ..servers.obsidian import ObsidianServer
from .db import MemoryDB


class MemoryHooks:
    """Lifecycle hooks that capture session context."""

    def __init__(self, db: MemoryDB | None = None):
        self.db = db or MemoryDB()

    def session_start(self, payload: dict) -> str:
        """Called on SessionStart. Injects relevant context."""
        _session_id = payload.get("session_id", "unknown")
        _project_path = payload.get("project_path", "")

        # Get recent observations for this project
        recent = self.db.get_recent(limit=5)
        if recent:
            context = "\n[Memory] Recent context:\n"
            for obs in recent:
                context += (
                    f"- [{obs['type']}] {obs['summary'] or obs['content'][:100]}\n"
                )
            return context
        return ""

    def post_tool_use(self, payload: dict) -> None:
        """Called on PostToolUse. Saves tool output."""
        session_id = payload.get("session_id", "unknown")
        tool_name = payload.get("tool", "")
        output = payload.get("output", "")

        if len(output) > 1000:
            output = output[:1000] + "... [truncated]"

        self.db.add_observation(
            session_id=session_id,
            obs_type="tool",
            content=output,
            summary=f"Used {tool_name}",
            tags=[tool_name],
        )

    def stop(self, payload: dict) -> None:
        """Called on Stop. Summarizes session."""
        session_id = payload.get("session_id", "unknown")
        # Could call LLM for summary here; for now, store raw
        self.db.add_observation(
            session_id=session_id,
            obs_type="session",
            content="Session ended",
            summary="Session completed",
            tags=["session"],
        )
        self._write_session_note(payload)

    def session_end(self, payload: dict) -> None:
        """Called on SessionEnd. Finalizes."""
        self._write_session_note(payload)

    def _default_vault_path(self) -> Path | None:
        """Return the configured default Obsidian vault, if any."""
        path = KimiConfig().get_default_memory_vault()
        if path:
            return Path(path).expanduser().resolve()
        return None

    def _write_session_note(self, payload: dict) -> None:
        """Persist a session summary to the default Obsidian vault."""
        vault_path = self._default_vault_path()
        if not vault_path:
            return

        # Ensure the vault is valid so obsidian-mcp recognizes anything we add.
        if not ObsidianServer.validate_vault(vault_path, fix=True):
            return

        session_id = payload.get("session_id", "unknown")
        project_path = payload.get("project_path", "")
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")

        recent = self.db.get_recent(session_id=session_id, limit=50)

        try:
            note_dir = vault_path / "Sessions"
            note_dir.mkdir(parents=True, exist_ok=True)
            note_path = note_dir / f"{timestamp}-{session_id[:8]}.md"

            lines = [
                f"# Session {timestamp}",
                "",
                f"- **Session ID:** `{session_id}`",
                f"- **Project:** `{project_path}`",
                "",
                "## Observations",
                "",
            ]
            for obs in recent:
                summary = obs["summary"] or obs["content"][:200]
                lines.append(f"- [{obs['type']}] {summary}")
            if not recent:
                lines.append("- No observations captured yet.")

            note_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except OSError:
            # Fail silently: memory hooks should not break the CLI session.
            return
