"""Kimi CLI hooks for automatic memory capture."""

import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from ..config import KimiConfig
from ..servers.obsidian import ObsidianServer
from .db import MemoryDB
from .summarizer import Summarizer

_logger = logging.getLogger(__name__)


def _sanitize_session_id(session_id: str) -> str:
    """Replace characters unsafe for filenames with underscores."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", session_id)


class MemoryHooks:
    """Lifecycle hooks that capture session context."""

    def __init__(self, db: MemoryDB | None = None):
        self.db = db or MemoryDB()

    def session_start(self, payload: dict) -> str:
        """Called on SessionStart. Injects relevant context."""
        project_path = payload.get("project_path", "")
        if project_path:
            project_path = str(Path(project_path).resolve())
        parts: list[str] = []

        recent = self.db.get_recent(limit=5)
        if recent:
            parts.append("\n[Memory] Recent context:")
            for obs in recent:
                parts.append(
                    f"- [{obs['type']}] {obs['summary'] or obs['content'][:100]}"
                )

        if project_path:
            memories = self.db.get_memories(
                limit=10, category="project", project_path=project_path
            )
            if memories:
                parts.append("\n[Memory] Project notes:")
                for mem in memories:
                    content = mem["content"]
                    if len(content) > 200:
                        content = content[:200] + "... [truncated]"
                    parts.append(f"- {content}")

        return "\n".join(parts)

    def post_tool_use(self, payload: dict) -> None:
        """Called on PostToolUse. Saves tool output."""
        session_id = payload.get("session_id", "unknown")
        tool_name = payload.get("tool", "")
        output = payload.get("output") or ""
        output = str(output)

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
        self.db.add_observation(
            session_id=session_id,
            obs_type="session",
            content="Session ended",
            summary="Session completed",
            tags=["session"],
        )
        self._write_session_notes(payload)

    def session_end(self, payload: dict) -> None:
        """Called on SessionEnd. No-op; finalization is handled in stop()."""
        pass

    def _default_vault_path(self) -> Path | None:
        """Return the configured default Obsidian vault, if any."""
        path = KimiConfig().get_default_memory_vault()
        if path:
            return Path(path).expanduser().resolve()
        return None

    def _write_session_notes(self, payload: dict) -> None:
        """Persist raw observations and an LLM summary to the default Obsidian vault."""
        vault_path = self._default_vault_path()
        if not vault_path:
            return

        if not ObsidianServer.validate_vault(vault_path, fix=True):
            return

        session_id = payload.get("session_id", "unknown")
        safe_session_id = _sanitize_session_id(session_id)
        project_path = payload.get("project_path", "")
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")

        recent = self.db.get_recent(session_id=session_id, limit=50)

        try:
            note_dir = vault_path / "Sessions"
            note_dir.mkdir(parents=True, exist_ok=True)

            raw_path = note_dir / f"{timestamp}-{safe_session_id}.md"
            raw_path.write_text(
                self._format_raw_note(timestamp, session_id, project_path, recent),
                encoding="utf-8",
            )

            try:
                summarizer = Summarizer.from_config()
                summary = summarizer.summarize_session(recent)
                if summary:
                    summary_path = note_dir / f"{timestamp}-{safe_session_id}-summary.md"
                    summary_path.write_text(
                        self._format_summary_note(
                            timestamp, session_id, project_path, summary
                        ),
                        encoding="utf-8",
                    )
            except Exception:
                _logger.debug(
                    "Failed to generate session summary", exc_info=True
                )
        except OSError:
            _logger.debug("Failed to write Obsidian session notes", exc_info=True)
            return

    def _format_raw_note(
        self,
        timestamp: str,
        session_id: str,
        project_path: str,
        observations: list[dict],
    ) -> str:
        lines = [
            f"# Session {timestamp}",
            "",
            f"- **Session ID:** `{session_id}`",
            f"- **Project:** `{project_path}`",
            "",
            "## Observations",
            "",
        ]
        for obs in observations:
            summary = obs["summary"] or obs["content"][:200]
            lines.append(f"- [{obs['type']}] {summary}")
        if not observations:
            lines.append("- No observations captured yet.")
        return "\n".join(lines) + "\n"

    def _format_summary_note(
        self,
        timestamp: str,
        session_id: str,
        project_path: str,
        summary: str,
    ) -> str:
        return (
            f"# Session Summary {timestamp}\n\n"
            f"- **Session ID:** `{session_id}`\n"
            f"- **Project:** `{project_path}`\n\n"
            f"{summary}\n"
        )
