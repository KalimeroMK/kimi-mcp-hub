"""OpenAI-compatible embedding client for semantic memory search.

Reads its settings from the ``[memory]`` section of
``~/.kimi-code/config.toml`` directly (rather than through KimiConfig) so the
memory module stays self-contained: ``summary_api_key`` and
``summary_base_url`` are shared with summarization, and the optional
``embedding_model`` key selects the model. Every failure -- missing
configuration, network errors, malformed responses -- is reported as
"unavailable" instead of raising, so capture and search paths never break.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Callable

import requests

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

_logger = logging.getLogger(__name__)


def load_embedding_settings() -> dict[str, str]:
    """Read embedding settings from the [memory] section of config.toml.

    KIMI_MEMORY_EMBEDDING_MODEL overrides the configured model.
    """
    path = Path.home() / ".kimi-code" / "config.toml"
    try:
        with path.open("rb") as f:
            memory = tomllib.load(f).get("memory", {})
    except (OSError, tomllib.TOMLDecodeError):
        memory = {}
    return {
        "api_key": str(memory.get("summary_api_key", "") or ""),
        "base_url": str(memory.get("summary_base_url", "") or ""),
        "model": str(
            os.environ.get("KIMI_MEMORY_EMBEDDING_MODEL")
            or memory.get("embedding_model")
            or ""
        ),
    }


class EmbeddingClient:
    """POSTs texts to ``{base_url}/embeddings`` (OpenAI-compatible).

    The constructor accepts an injectable ``embed`` callable so tests can
    supply deterministic vectors without any network access.
    """

    def __init__(
        self,
        api_key: str = "",
        model: str = "",
        base_url: str = "",
        embed: Callable[[list[str]], list[list[float]]] | None = None,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._embed = embed

    @classmethod
    def from_config(
        cls, embed: Callable[[list[str]], list[list[float]]] | None = None
    ) -> "EmbeddingClient":
        settings = load_embedding_settings()
        return cls(
            api_key=settings["api_key"],
            model=settings["model"],
            base_url=settings["base_url"],
            embed=embed,
        )

    @property
    def available(self) -> bool:
        """Return True when the client can produce embeddings."""
        if self._embed is not None:
            return True
        return bool(self.api_key and self.model and self.base_url)

    def embed(self, texts: list[str]) -> list[list[float]] | None:
        """Return one vector per text, or None when unavailable."""
        if not texts or not self.available:
            return None
        if self._embed is not None:
            try:
                return self._embed(texts)
            except Exception:
                _logger.warning("Embedding callable failed", exc_info=True)
                return None
        try:
            response = requests.post(
                f"{self.base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": self.model, "input": texts},
                timeout=30,
            )
            if not response.ok:
                _logger.warning(
                    "Embedding request failed: HTTP %s from %s",
                    response.status_code,
                    self.base_url,
                )
                return None
            data = response.json()["data"]
            data.sort(key=lambda item: item["index"])
            return [item["embedding"] for item in data]
        except Exception:  # network, JSON, or shape errors all mean unavailable
            _logger.warning("Embedding request failed", exc_info=True)
            return None
