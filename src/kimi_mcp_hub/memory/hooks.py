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
from .db import MemoryDB
from .summarizer import Summarizer

_logger = logging.getLogger(__name__)


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

    def session_start(self, payload: dict) -> str:
        """Called on SessionStart. Injects relevant context."""
        # Kimi CLI sends the working directory as ``cwd``; keep ``project_path``
        # as a fallback for tests and alternative callers.
        project_path = payload.get("cwd") or payload.get("project_path", "")
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

        if _is_image_output(raw_output):
            content = self._persist_image_output(raw_output, session_id, tool_name)
        else:
            content = _extract_text_output(raw_output)
            if len(content) > 1000:
                content = content[:1000] + "... [truncated]"

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
        # Kimi CLI sends the working directory as ``cwd``; keep ``project_path``
        # as a fallback for tests and alternative callers. If neither is present,
        # fall back to the process working directory so the note still has context.
        project_path = (
            payload.get("cwd") or payload.get("project_path") or str(Path.cwd())
        )
        _debug_log_payload(
            {
                "session_id": session_id,
                "payload_keys": list(payload.keys())
                if isinstance(payload, dict)
                else [],
                "cwd": payload.get("cwd"),
                "project_path": payload.get("project_path"),
                "resolved_project_path": project_path,
                "observation_count": len(
                    self.db.get_recent(session_id=session_id, limit=50)
                ),
            },
            "stop",
        )
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
                    summary_path = (
                        note_dir / f"{timestamp}-{safe_session_id}-summary.md"
                    )
                    summary_path.write_text(
                        self._format_summary_note(
                            timestamp, session_id, project_path, summary
                        ),
                        encoding="utf-8",
                    )
            except Exception:
                _logger.debug("Failed to generate session summary", exc_info=True)
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
