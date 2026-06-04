"""Plugin tools for Kimi AI to query memory."""

from .db import MemoryDB


class MemoryPlugin:
    """Tools that Kimi AI can call to query its own memory."""

    def __init__(self, db: MemoryDB | None = None):
        self.db = db or MemoryDB()

    def memory_search(self, query: str, limit: int = 10) -> str:
        """Search memory by keyword."""
        results = self.db.search(query, limit=limit)
        if not results:
            return "No matching memories found."
        output = "Memory results:\n"
        for r in results:
            output += f"- [{r['type']}] {r['summary'] or r['content'][:200]}\n"
        return output

    def memory_timeline(self, limit: int = 20) -> str:
        """Show recent memory timeline."""
        results = self.db.get_recent(limit=limit)
        if not results:
            return "No memories yet."
        output = "Recent timeline:\n"
        for r in results:
            output += f"- {r['timestamp'][:10]} [{r['type']}] {r['summary'] or r['content'][:150]}\n"
        return output

    def memory_get(self, obs_id: int) -> str:
        """Get full observation by ID."""
        # This would need a get_by_id method in DB
        return f"Observation {obs_id} details..."
