"""LLM-powered session summarization for Obsidian memory."""

from __future__ import annotations

import logging
from typing import Any

import requests

_logger = logging.getLogger(__name__)

_CONTENT_PREVIEW_LEN = 200

PROMPT_TEMPLATE = """You are summarizing a coding session. Given the following observations,
write a summary in exactly this shape:

Title: one specific sentence, at most 90 characters, naming what was actually
done. Write it so someone scanning a list of past sessions months later knows
whether this one is relevant. No generic words like "summary", "session" or
"various changes".

Then a markdown body with these sections:

- Goal: what the user was trying to accomplish
- Key decisions: important choices made during the session
- Files and tools touched: relevant files, commands, MCP tools
- Open questions / TODOs: anything unresolved or left to do

Keep the body under 300 words. Use bullet points. Do not include raw output dumps.

Observations:
{observations}
"""


SYSTEM_PROMPT = "You are a helpful coding session summarizer."


class Summarizer:
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        temperature: float | None = None,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        # Omitted from the request unless configured. Reasoning models reject
        # anything but their own default -- Kimi's coding endpoint answers
        # "only 1 is allowed for this model" -- so sending one unasked turns
        # every summary into a 400.
        self.temperature = temperature

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
            temperature=cfg.get_memory_summary_temperature(),
        )

    def _request(self, prompt: str, max_tokens: int | None = None):
        """Send one chat completion. Shared so a check cannot drift from the
        real call and report success for a request shape never actually used.
        """
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        }
        if self.temperature is not None:
            body["temperature"] = self.temperature
        if max_tokens is not None:
            body["max_tokens"] = max_tokens

        return requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=30,
        )

    def check(self) -> tuple[bool, str]:
        """Verify the configured credentials with one minimal request.

        Summarization runs inside the Stop hook, where a failure can only be
        logged to a stream nobody reads -- a bad key therefore stays invisible
        while every session silently loses its summary. This makes the failure
        answerable on demand.
        """
        if not self.api_key:
            return False, "no API key configured"
        try:
            response = self._request("Reply with the word: ok", max_tokens=16)
        except requests.RequestException as exc:
            return False, f"could not reach {self.base_url}: {exc}"

        if response.status_code == 401:
            return False, f"the API key was rejected (401) by {self.base_url}"
        if response.status_code == 404:
            return False, f"model {self.model!r} not found at {self.base_url}"
        if not response.ok:
            detail = response.text[:200].replace("\n", " ")
            return False, f"HTTP {response.status_code}: {detail}"
        return True, f"{self.model} responded at {self.base_url}"

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
                lines.append(
                    f"- [{obs.get('type', 'unknown')}] {summary or content or 'No details'}"
                )
        return PROMPT_TEMPLATE.format(
            observations="\n".join(lines) if lines else "- No observations."
        )

    def summarize_session(self, observations: list[dict[str, Any]]) -> str | None:
        if not self.api_key:
            _logger.debug("No API key configured; skipping session summary")
            return None

        prompt = self._build_prompt(observations)
        try:
            response = self._request(prompt)
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
