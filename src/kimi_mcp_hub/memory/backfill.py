"""Recover project attribution for observations captured before it existed.

Until observations started recording the working directory, every row was
written with a NULL ``project_path``, which project-scoped recall cannot see.
The session notes in the Obsidian vault do carry the project, so the mapping
can be reconstructed from them:

    - **Session ID:** `session_5577283c-...`
    - **Project:** `/Users/me/PhpstormProjects/app`

Both the raw note and the summary note repeat those fields, so a session is
recoverable as long as either survives.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from .db import MemoryDB

_SESSION_RE = re.compile(r"^-\s+\*\*Session ID:\*\*\s+`([^`]*)`", re.M)
_PROJECT_RE = re.compile(r"^-\s+\*\*Project:\*\*\s+`([^`]*)`", re.M)


@dataclass
class BackfillPlan:
    """What a backfill would change, before anything is written."""

    notes_scanned: int = 0
    notes_without_project: int = 0
    sessions_mapped: int = 0
    sessions_matched: int = 0
    observations_to_update: int = 0
    per_project: dict[str, int] = field(default_factory=dict)
    conflicts: dict[str, set[str]] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return self.observations_to_update == 0


def _resolve(path: str) -> str:
    """Normalize a recorded path the same way new observations are stored."""
    try:
        return str(Path(path).resolve())
    except OSError:
        return path


def parse_session_notes(vault_path: Path) -> tuple[dict[str, str], BackfillPlan]:
    """Map session id -> project path from the notes in ``vault_path``.

    A session whose notes disagree about the project is left out rather than
    guessed at; the disagreement is reported on the plan instead.
    """
    plan = BackfillPlan()
    candidates: dict[str, set[str]] = defaultdict(set)

    sessions_dir = Path(vault_path) / "Sessions"
    if not sessions_dir.is_dir():
        return {}, plan

    for note in sorted(sessions_dir.glob("*.md")):
        try:
            text = note.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        plan.notes_scanned += 1

        session_match = _SESSION_RE.search(text)
        project_match = _PROJECT_RE.search(text)
        if not session_match:
            continue
        session_id = session_match.group(1).strip()
        project = project_match.group(1).strip() if project_match else ""
        if not session_id:
            continue
        if not project:
            plan.notes_without_project += 1
            continue
        candidates[session_id].add(_resolve(project))

    mapping: dict[str, str] = {}
    for session_id, projects in candidates.items():
        if len(projects) == 1:
            mapping[session_id] = next(iter(projects))
        else:
            plan.conflicts[session_id] = projects

    plan.sessions_mapped = len(mapping)
    return mapping, plan


def build_plan(
    db: MemoryDB, mapping: dict[str, str], plan: BackfillPlan
) -> BackfillPlan:
    """Count the observations a backfill would touch, without writing."""
    counts = db.count_unattributed_by_session(list(mapping))
    for session_id, count in counts.items():
        project = mapping[session_id]
        plan.per_project[project] = plan.per_project.get(project, 0) + count
        plan.observations_to_update += count
        plan.sessions_matched += 1
    return plan


def apply_plan(db: MemoryDB, mapping: dict[str, str]) -> int:
    """Write the recovered project paths. Returns the number of rows updated.

    Only rows that still have no project are touched, so running this twice
    changes nothing the second time and it never overwrites the more reliable
    attribution that newer observations carry.
    """
    by_project: dict[str, list[str]] = defaultdict(list)
    for session_id, project in mapping.items():
        by_project[project].append(session_id)
    return db.attribute_sessions_to_projects(by_project)
