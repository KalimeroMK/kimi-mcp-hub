"""CLI entry point for Kimi memory hooks.

Kimi CLI passes hook payloads as JSON on stdin. This script reads stdin,
dispatches to MemoryHooks, and prints any additional context returned by
the hook (e.g., SessionStart context injection).
"""

import json
import sys

from kimi_mcp_hub.memory.hooks import MemoryHooks


EVENT_MAP = {
    "session_start": "session_start",
    "post_tool_use": "post_tool_use",
    "stop": "stop",
    "session_end": "session_end",
}


def main() -> int:
    event = sys.argv[1] if len(sys.argv) > 1 else "stop"
    method_name = EVENT_MAP.get(event, event)

    try:
        payload = json.load(sys.stdin) if not sys.stdin.isatty() else {}
    except json.JSONDecodeError:
        payload = {}

    hooks = MemoryHooks()
    method = getattr(hooks, method_name, None)
    if method is None:
        print(f"Unknown memory hook event: {event}", file=sys.stderr)
        return 1

    result = method(payload)
    if result:
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
