"""Kimi CLI hooks for automatic memory capture."""

import base64
import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import KimiConfig
from ..servers.obsidian import ObsidianServer
from .context import build_context
from .db import MemoryDB, content_hash
from .summarizer import Summarizer

_logger = logging.getLogger(__name__)

# Read-only navigation tools whose *output* is bulk noise. The call is still
# recorded (so the timeline stays complete) but the body is dropped, which
# keeps the observations table from filling up with file dumps and grep hits.
_NOISY_TOOLS = frozenset(
    {
        "Read",
        "Glob",
        "Grep",
        "LS",
        "NotebookRead",
        "TodoRead",
        "TodoWrite",
        "WebFetch",
        "WebSearch",
    }
)


def _resolve_project_path(payload: dict) -> str:
    """Return the absolute project path for a hook payload.

    Kimi CLI sends the working directory as ``cwd``; ``project_path`` is kept
    as a fallback for tests and alternative callers. Falling back to the
    process working directory guarantees observations are always attributable
    to a project, which is what makes project-scoped recall possible.
    """
    raw = payload.get("cwd") or payload.get("project_path") or str(Path.cwd())
    try:
        return str(Path(raw).resolve())
    except OSError:
        return str(raw)


_TITLE_PREFIX_RE = re.compile(r"^(?:#+\s*)?(?:\*\*)?title(?:\*\*)?\s*[:\-]\s*", re.I)
# Headings the model may emit before the real title, plus the section names of
# the summary template itself. None of them identify a session.
_GENERIC_TITLES = frozenset(
    {
        "summary",
        "session summary",
        "coding session summary",
        "session",
        "overview",
        "goal",
        "goals",
        "key decisions",
        "decisions",
        "files and tools touched",
        "files touched",
        "tools touched",
        "open questions",
        "open questions / todos",
        "todos",
        "todo",
        "next steps",
        "notes",
    }
)


def _first_line(text: str | None, limit: int = 160) -> str:
    """Return a usable title for a session summary.

    The summary prompt asks for a leading ``Title:`` line, but models still
    sometimes lead with a generic heading. Those are skipped so the session
    list shows what actually happened instead of a column of "Summary".
    """
    if not text:
        return ""
    fallback = ""
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if _TITLE_PREFIX_RE.match(stripped):
            titled = _TITLE_PREFIX_RE.sub("", stripped).strip(" *#")
            if titled:
                return titled[:limit]
            continue
        cleaned = stripped.lstrip("#").strip(" *-")
        if not cleaned:
            continue
        if cleaned.lower().rstrip(".:") in _GENERIC_TITLES:
            continue
        if not fallback:
            fallback = cleaned
    return fallback[:limit]


def _noisy_tools() -> frozenset[str]:
    """Return the set of tools whose output body is not stored."""
    if os.environ.get("KIMI_MEMORY_CAPTURE_ALL"):
        return frozenset()
    extra = os.environ.get("KIMI_MEMORY_SKIP_TOOLS", "")
    if not extra:
        return _NOISY_TOOLS
    return _NOISY_TOOLS | {name.strip() for name in extra.split(",") if name.strip()}


def _debug_log_payload(payload: dict, source: str) -> None:
    """Append the raw hook payload to a debug log file.

    Only active when the ``KIMI_MEMORY_HOOK_DEBUG`` environment variable is
    set, so normal sessions don't grow an unbounded log on every tool call.
    The log lives next to the memory database so it is easy to find and share.
    """
    if not os.environ.get("KIMI_MEMORY_HOOK_DEBUG"):
        return
    try:
        log_path = Path(KimiConfig().hub_dir) / "hook-debug.log"
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "payload": payload,
        }
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass


def _sanitize_session_id(session_id: str) -> str:
    """Replace characters unsafe for filenames with underscores."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", session_id)


def _looks_like_base64(value: str) -> bool:
    """Return True if ``value`` is valid base64."""
    try:
        base64.b64decode(value, validate=True)
        return True
    except Exception:
        return False


def _is_image_output(output: Any) -> bool:
    """Return True if ``output`` appears to contain image data or a URL."""
    if isinstance(output, str):
        return output.startswith("data:image") or (
            len(output) > 100 and _looks_like_base64(output)
        )
    if isinstance(output, dict):
        if output.get("isImage") is True or output.get("imageData"):
            return True
        return (
            output.get("type") == "image"
            or any(k in output for k in ("image_url", "url", "mime_type", "media_type"))
            or "source" in output
        )
    if isinstance(output, list):
        return any(_is_image_output(item) for item in output)
    return False


def _image_url(output: Any) -> str | None:
    """Return a markdown-compatible image URL if ``output`` contains one."""
    if isinstance(output, list):
        for item in output:
            url = _image_url(item)
            if url:
                return url
        return None
    if isinstance(output, dict):
        url = output.get("image_url") or output.get("url")
        if isinstance(url, str) and url.startswith(("http://", "https://", "/")):
            return url
    return None


def _extract_text_output(output: Any) -> str:
    """Convert a tool response (string, dict, or list) into readable text.

    Dicts with ``stdout``/``stderr`` or ``output``/``result``/``content`` keys
    are flattened; everything else is serialized as compact JSON so the note
    stays readable and searchable.
    """
    if output is None:
        return ""
    if isinstance(output, str):
        return output
    if isinstance(output, dict):
        if output.get("stdout") is not None or output.get("stderr"):
            parts = []
            if output.get("stdout"):
                parts.append(str(output["stdout"]))
            if output.get("stderr"):
                parts.append(f"stderr: {output['stderr']}")
            return "\n".join(parts)
        for key in ("output", "result", "content", "text"):
            if key in output and output[key] is not None:
                value = output[key]
                return value if isinstance(value, str) else json.dumps(value)
        return json.dumps(output, ensure_ascii=False)
    if isinstance(output, list):
        texts = []
        for item in output:
            if isinstance(item, dict) and item.get("type") == "text":
                texts.append(str(item.get("text", "")))
            elif not _is_image_output(item):
                texts.append(_extract_text_output(item))
        return "\n".join(texts)
    return str(output)


def _extract_image_bytes(output: Any) -> tuple[bytes, str] | None:
    """Return (image_bytes, extension) from ``output`` if it carries image data."""
    if isinstance(output, list):
        for item in output:
            extracted = _extract_image_bytes(item)
            if extracted:
                return extracted
        return None

    if isinstance(output, dict):
        image_data = output.get("imageData")
        if image_data and isinstance(image_data, str):
            try:
                return (base64.b64decode(image_data), "png")
            except Exception:
                pass

        source = output.get("source")
        if isinstance(source, dict):
            data = source.get("data") or ""
            media_type = source.get("media_type", "image/png")
            ext = media_type.split("/")[-1] or "png"
            try:
                return (base64.b64decode(data), ext)
            except Exception:
                return None

        data = output.get("data") or output.get("base64") or ""
        mime = output.get("mime_type") or output.get("media_type") or "image/png"
        ext = mime.split("/")[-1] or "png"
        try:
            return (base64.b64decode(data), ext)
        except Exception:
            return None

    if isinstance(output, str):
        if output.startswith("data:image"):
            header, _, b64 = output.partition(";base64,")
            ext = header.split("/")[-1] if "/" in header else "png"
            try:
                return (base64.b64decode(b64), ext)
            except Exception:
                return None
        try:
            return (base64.b64decode(output), "png")
        except Exception:
            return None

    return None


class MemoryHooks:
    """Lifecycle hooks that capture session context."""

    def __init__(self, db: MemoryDB | None = None):
        self.db = db or MemoryDB()

    def _maybe_start_viewer(self) -> None:
        """Bring the background viewer up if the user opted into autostart.

        Deliberately silent and best-effort: this runs on every session start
        under a short hook timeout, so it must not slow the session down and
        must never let a viewer problem break one. The URL is stable, so there
        is nothing to announce each time -- ``memory viewer --status`` prints it.
        """
        try:
            config = KimiConfig()
            if not config.is_viewer_autostart_enabled():
                return
            from .viewer import start_daemon

            start_daemon(port=config.get_viewer_port())
        except Exception:
            _logger.debug("Failed to autostart the memory viewer", exc_info=True)

    def session_start(self, payload: dict) -> str:
        """Called on SessionStart. Injects relevant context."""
        self._maybe_start_viewer()
        project_path = payload.get("cwd") or payload.get("project_path", "")
        if project_path:
            project_path = str(Path(project_path).resolve())

        config = KimiConfig()
        return build_context(
            self.db,
            project_path or None,
            max_sessions=config.get_context_sessions(),
            max_notes=config.get_context_notes(),
        )

    def user_prompt_submit(self, payload: dict) -> str:
        """Called on UserPromptSubmit. Injects memory relevant to this prompt.

        SessionStart can only inject what was recent; this hook retrieves by
        relevance to what the user just asked, which is where cross-session
        memory actually pays off.
        """
        prompt = (
            payload.get("prompt")
            or payload.get("user_prompt")
            or payload.get("message")
            or ""
        )
        if not isinstance(prompt, str) or len(prompt.strip()) < 8:
            return ""

        project_path = _resolve_project_path(payload)
        # match_any: the prompt is a sentence, so requiring every word to be
        # present would retrieve nothing.
        memories = self.db.search_memories(
            prompt, limit=3, project_path=project_path, match_any=True
        )
        observations = self.db.search_index(
            prompt,
            limit=5,
            project_path=project_path,
            obs_type="session",
            match_any=True,
        )
        if not memories and not observations:
            return ""

        parts = ["\n[Memory] Possibly relevant to this request:"]
        for mem in memories:
            content = mem["content"]
            if len(content) > 200:
                content = content[:200] + "... [truncated]"
            parts.append(f"- (note) {content}")
        for obs in observations:
            summary = obs.get("summary") or ""
            parts.append(f"- (#{obs['id']}) {summary}")
        if observations:
            parts.append("[Memory] Fetch details with memory_get([ids]).")
        return "\n".join(parts)

    def post_tool_use(self, payload: dict) -> None:
        """Called on PostToolUse. Saves tool output."""
        session_id = payload.get("session_id", "unknown")
        # Different CLI versions/harnesses send the tool name under different
        # keys. Try the common ones and fall back to a generic label.
        tool_name = (
            payload.get("tool_name") or payload.get("name") or payload.get("tool", "")
        )
        # Claude Code / Kimi Code CLI send the result as ``tool_response``;
        # older harnesses used ``tool_output`` or just ``output``/``result``.
        raw_output = (
            payload.get("tool_response")
            or payload.get("tool_output")
            or payload.get("output")
            or payload.get("result")
            or ""
        )

        project_path = _resolve_project_path(payload)

        if _is_image_output(raw_output):
            content = self._persist_image_output(raw_output, session_id, tool_name)
        elif tool_name in _noisy_tools():
            # Keep the call in the timeline, drop the payload. A file dump or a
            # page of grep hits is bulk that crowds out the useful signal.
            content = f"[{tool_name} output omitted]"
        else:
            content = _extract_text_output(raw_output)
            if len(content) > 1000:
                content = content[:1000] + "... [truncated]"

        digest = content_hash(tool_name, content)
        if self.db.has_observation(session_id, digest):
            # Same tool, same result, same session -- nothing new to remember.
            return

        _debug_log_payload(
            {
                "session_id": session_id,
                "tool_name": tool_name,
                "raw_output_keys": list(payload.keys())
                if isinstance(payload, dict)
                else [],
                "raw_output_type": type(raw_output).__name__,
                "raw_output_preview": str(raw_output)[:200],
                "content_preview": content[:200],
            },
            "post_tool_use",
        )

        self.db.add_observation(
            session_id=session_id,
            obs_type="tool",
            content=content,
            summary=f"Used {tool_name}" if tool_name else "Used tool",
            tags=[tool_name] if tool_name else ["tool"],
            project_path=project_path,
            content_hash_value=digest,
        )

    def _persist_image_output(
        self, output: Any, session_id: str, tool_name: str
    ) -> str:
        """Save an image to the default vault and return a markdown reference.

        If no vault is configured or the image cannot be decoded, a short
        placeholder is returned so the note still records that an image was
        captured.
        """
        vault_path = self._default_vault_path()
        if not vault_path or not ObsidianServer.validate_vault(vault_path, fix=True):
            return "[Image captured]"

        url = _image_url(output)
        if url:
            return f"![{tool_name}]({url})"

        extracted = _extract_image_bytes(output)
        if not extracted:
            return "[Image captured]"

        image_bytes, ext = extracted
        safe_tool = _sanitize_session_id(tool_name) or "image"
        safe_session = _sanitize_session_id(session_id) or "session"
        digest = hashlib.sha256(image_bytes).hexdigest()[:8]
        filename = f"{safe_session}-{safe_tool}-{digest}.{ext}"

        attach_dir = vault_path / "Attachments"
        attach_dir.mkdir(parents=True, exist_ok=True)
        image_path = attach_dir / filename
        image_path.write_bytes(image_bytes)

        rel_path = image_path.relative_to(vault_path).as_posix()
        return f"![{tool_name}]({rel_path})"

    def stop(self, payload: dict) -> None:
        """Called on Stop. Summarizes the session and stores it as memory."""
        session_id = payload.get("session_id", "unknown")
        project_path = _resolve_project_path(payload)
        observations = self.db.get_recent(session_id=session_id, limit=50)

        summary_text = self._summarize(observations)

        # Store the summary itself so past sessions are searchable. The old
        # placeholder ("Session ended") carried no retrievable signal.
        self.db.add_observation(
            session_id=session_id,
            obs_type="session",
            content=summary_text or "Session ended",
            summary=_first_line(summary_text) or "Session completed",
            tags=["session"],
            project_path=project_path,
        )
        self._write_session_notes(
            payload, observations=observations, summary=summary_text
        )

    def _summarize(self, observations: list[dict]) -> str | None:
        """Return an LLM summary of the session, or None if unavailable."""
        try:
            return Summarizer.from_config().summarize_session(observations) or None
        except Exception:
            _logger.debug("Failed to generate session summary", exc_info=True)
            return None

    def session_end(self, payload: dict) -> None:
        """Called on SessionEnd. No-op; finalization is handled in stop()."""
        pass

    def _default_vault_path(self) -> Path | None:
        """Return the configured default Obsidian vault, if any."""
        path = KimiConfig().get_default_memory_vault()
        if path:
            return Path(path).expanduser().resolve()
        return None

    def _write_session_notes(
        self,
        payload: dict,
        observations: list[dict] | None = None,
        summary: str | None = None,
    ) -> None:
        """Persist raw observations and an LLM summary to the default Obsidian vault."""
        vault_path = self._default_vault_path()
        if not vault_path:
            return

        if not ObsidianServer.validate_vault(vault_path, fix=True):
            return

        session_id = payload.get("session_id", "unknown")
        safe_session_id = _sanitize_session_id(session_id)
        project_path = _resolve_project_path(payload)
        _debug_log_payload(
            {
                "session_id": session_id,
                "payload_keys": list(payload.keys())
                if isinstance(payload, dict)
                else [],
                "cwd": payload.get("cwd"),
                "project_path": payload.get("project_path"),
                "resolved_project_path": project_path,
                "observation_count": len(observations or []),
            },
            "stop",
        )
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")

        if observations is None:
            observations = self.db.get_recent(session_id=session_id, limit=50)
        if summary is None:
            summary = self._summarize(observations)

        try:
            note_dir = vault_path / "Sessions"
            note_dir.mkdir(parents=True, exist_ok=True)

            raw_path = note_dir / f"{timestamp}-{safe_session_id}.md"
            raw_path.write_text(
                self._format_raw_note(
                    timestamp, session_id, project_path, observations
                ),
                encoding="utf-8",
            )

            if summary:
                summary_path = note_dir / f"{timestamp}-{safe_session_id}-summary.md"
                summary_path.write_text(
                    self._format_summary_note(
                        timestamp, session_id, project_path, summary
                    ),
                    encoding="utf-8",
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
            summary = obs.get("summary") or ""
            content = obs.get("content") or ""
            if content.strip().startswith("!["):
                lines.append(f"- [{obs['type']}] {content}")
            elif summary and content and summary not in content:
                preview = (
                    content[:300] if len(content) <= 300 else content[:300] + "..."
                )
                lines.append(f"- [{obs['type']}] {summary}: {preview}")
            elif summary:
                lines.append(f"- [{obs['type']}] {summary}")
            elif content:
                preview = (
                    content[:300] if len(content) <= 300 else content[:300] + "..."
                )
                lines.append(f"- [{obs['type']}] {preview}")
            else:
                lines.append(f"- [{obs['type']}] No details")
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
