"""LLM-powered session summarization for Obsidian memory."""

from __future__ import annotations

import logging
from typing import Any

import requests

_logger = logging.getLogger(__name__)

_CONTENT_PREVIEW_LEN = 200

PROMPT_TEMPLATE = """You are summarizing a coding session. Given the following observations,
write a concise markdown summary with these sections:

- Goal: what the user was trying to accomplish
- Key decisions: important choices made during the session
- Files and tools touched: relevant files, commands, MCP tools
- Open questions / TODOs: anything unresolved or left to do

Keep it under 300 words. Use bullet points. Do not include raw output dumps.

Observations:
{observations}
"""


class Summarizer:
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    @classmethod
    def from_config(cls, config: Any | None = None) -> "Summarizer":
        from ..config import KimiConfig

        cfg = config or KimiConfig()
        if not cfg.is_memory_summary_enabled():
            _logger.debug("Memory summaries disabled; returning empty Summarizer")
            return cls(api_key="", model="", base_url="")

        return cls(
            api_key=cfg.get_memory_summary_api_key(),
            model=cfg.get_memory_summary_model(),
            base_url=cfg.get_memory_summary_base_url(),
        )

    def _build_prompt(self, observations: list[dict[str, Any]]) -> str:
        """Build a markdown prompt from the given observations.

        Each observation is expected to be a dict with optional ``type``,
        ``summary``, and ``content`` keys. Long ``content`` values are truncated
        to ``_CONTENT_PREVIEW_LEN`` characters so the prompt stays compact.
        """
        lines = []
        for obs in observations:
            summary = obs.get("summary")
            content = obs.get("content", "")[:_CONTENT_PREVIEW_LEN]
            if summary and content:
                lines.append(f"- [{obs.get('type', 'unknown')}] {summary}: {content}")
            else:
                lines.append(f"- [{obs.get('type', 'unknown')}] {summary or content or 'No details'}")
        return PROMPT_TEMPLATE.format(observations="\n".join(lines) if lines else "- No observations.")

    def summarize_session(self, observations: list[dict[str, Any]]) -> str | None:
        if not self.api_key:
            _logger.debug("No API key configured; skipping session summary")
            return None

        prompt = self._build_prompt(observations)
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are a helpful coding session summarizer."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            if (
                not isinstance(data, dict)
                or not isinstance(data.get("choices"), list)
                or len(data["choices"]) == 0
                or not isinstance(data["choices"][0], dict)
                or not isinstance(data["choices"][0].get("message"), dict)
                or "content" not in data["choices"][0]["message"]
            ):
                _logger.warning("Unexpected LLM response shape: %s", data)
                return None
            return data["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            _logger.warning("Session summarization failed: %s", exc)
            return None
