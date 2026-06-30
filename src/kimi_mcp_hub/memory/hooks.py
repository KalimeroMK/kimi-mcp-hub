"""Kimi CLI hooks for automatic memory capture."""

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

    def session_end(self, payload: dict) -> None:
        """Called on SessionEnd. Finalizes."""
        pass
