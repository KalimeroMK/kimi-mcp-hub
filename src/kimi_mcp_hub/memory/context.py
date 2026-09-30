"""The memory block injected at the start of a Kimi session.

What goes in here is spent from every session's context window, so it has to
earn its place. Two things do:

* **Project notes** -- things deliberately written down to be remembered.
* **Past sessions** -- one titled line each, with an id to pull the rest.

Captured tool calls do not. "Used Bash" repeated eight times says nothing a
model can act on, and the detail behind it is one ``memory_get`` away. They
appear only when a project has no summarized sessions yet, so a new user still
sees that memory is working.
"""

from __future__ import annotations

from datetime import datetime

# Titles written before session summarization worked, or when it fails. They
# identify nothing, so a line spent on them is a line wasted.
_PLACEHOLDER_TITLES = frozenset(
    {"session completed", "session ended", "session", "summary"}
)

DEFAULT_MAX_SESSIONS = 8
DEFAULT_MAX_NOTES = 5
DEFAULT_MAX_FALLBACK = 5


def _is_placeholder(title: str | None) -> bool:
    return not title or title.strip().lower().rstrip(".") in _PLACEHOLDER_TITLES


def _parse(timestamp: str) -> datetime | None:
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        return None


def _day(timestamp: str) -> str:
    """Format an ISO timestamp as a date heading.

    Falls back to parsing just the date part: a timestamp the full parser
    rejects would otherwise render as a raw string and, worse, split one day
    into two headings because the two spellings never compare equal.
    """
    parsed = _parse(timestamp) or _parse((timestamp or "")[:10])
    if parsed:
        return parsed.strftime("%b %d, %Y")
    return timestamp[:10] if timestamp else "unknown"


def _clock(timestamp: str) -> str:
    parsed = _parse(timestamp)
    return parsed.strftime("%H:%M") if parsed else ""


def _truncate(text: str, limit: int) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def build_context(
    db,
    project_path: str | None,
    *,
    max_sessions: int = DEFAULT_MAX_SESSIONS,
    max_notes: int = DEFAULT_MAX_NOTES,
    project_label: str | None = None,
) -> str:
    """Render the session-start memory block. Empty string when there is nothing."""
    scope = project_path or None

    notes = (
        db.get_memories(limit=max_notes, category="project", project_path=scope)
        if scope
        else []
    )

    # Over-fetch: placeholder-titled sessions are dropped, and on an older
    # database most of them are.
    raw_sessions = db.get_recent(
        limit=max_sessions * 6, obs_type="session", project_path=scope
    )
    sessions = [row for row in raw_sessions if not _is_placeholder(row.get("summary"))][
        :max_sessions
    ]

    fallback: list[dict] = []
    if not sessions and not notes:
        fallback = [
            row
            for row in db.get_recent(limit=DEFAULT_MAX_FALLBACK * 3, project_path=scope)
            if row["type"] != "meta"
        ][:DEFAULT_MAX_FALLBACK]
        if not fallback:
            return ""

    label = project_label or (
        scope.rstrip("/").rsplit("/", 1)[-1] if scope else "all projects"
    )
    lines = [f"\n# Memory — {label}"]

    if notes:
        lines.append("\n## Project notes")
        for note in notes:
            lines.append(f"- {_truncate(note['content'], 200)}")

    if sessions:
        lines.append("\n## Past sessions")
        current_day = ""
        for row in sessions:
            day = _day(row["timestamp"])
            if day != current_day:
                lines.append(f"\n### {day}")
                current_day = day
            lines.append(
                f"[#{row['id']}] {_clock(row['timestamp'])}  {_truncate(row['summary'], 110)}"
            )

    if fallback:
        lines.append("\n## Recent activity")
        for row in fallback:
            title = row.get("summary") or _truncate(row.get("content", ""), 80)
            lines.append(f"[#{row['id']}] {_clock(row['timestamp'])}  {title}")

    lines.append(_footer(db, scope, shown=len(sessions) + len(fallback)))
    return "\n".join(lines)


def _footer(db, scope: str | None, shown: int) -> str:
    """State what is on offer and how to reach it.

    Real counts only: an invented "savings" percentage would tell the model
    nothing it can act on, whereas knowing 37,000 observations are one call
    away changes whether it bothers to look.
    """
    stats = db.get_stats()
    parts = []
    if scope:
        _, project_total = db.browse_observations(limit=0, project_path=scope)
        parts.append(f"{project_total:,} observations here")
    parts.append(f"{stats.get('total_observations', 0):,} total")
    parts.append(f"{stats.get('total_sessions', 0):,} sessions")

    return (
        f"\n---\n{shown} shown · " + " · ".join(parts) + "\n"
        "Read one: memory_get([id]) · Around it: memory_timeline(id) · "
        'Search all: memory_search("terms")'
    )
