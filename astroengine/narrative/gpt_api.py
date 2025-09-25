"""GPT-backed narrative helpers with graceful fallbacks."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from typing import Any

LOG = logging.getLogger(__name__)

__all__ = ["GPTNarrativeClient"]

Transport = Callable[[str, str, float], str]


class GPTNarrativeClient:
    """Wrapper around OpenAI-compatible chat APIs."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        model: str = "gpt-3.5-turbo",
        transport: Callable[..., str] | None = None,
        allow_stub: bool = True,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self._transport = transport
        self._openai: Any | None = None
        if transport is None and api_key:
            try:  # pragma: no cover - requires optional dependency
                import openai  # type: ignore
            except Exception as exc:  # pragma: no cover
                if not allow_stub:
                    raise
                LOG.warning("OpenAI client unavailable: %s", exc)
            else:
                self._openai = openai
                self._openai.api_key = api_key

    @classmethod
    def from_env(
        cls,
        *,
        model: str = "gpt-3.5-turbo",
        transport: Callable[..., str] | None = None,
    ) -> GPTNarrativeClient:
        api_key = os.getenv("ASTROENGINE_OPENAI_KEY") or os.getenv("OPENAI_API_KEY")
        return cls(api_key, model=model, transport=transport)

    def summarize(self, prompt: str, *, temperature: float = 0.2) -> str:
        """Return a summary for ``prompt`` using the configured backend."""

        if self._transport is not None:
            return self._transport(prompt, model=self.model, temperature=temperature)
        if self._openai is None:
            raise RuntimeError("No GPT backend configured")
        response = self._openai.ChatCompletion.create(  # type: ignore[call-arg]
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        choice = response.get("choices", [{}])[0]
        message = choice.get("message", {})
        return str(message.get("content", "")).strip()

    @property
    def available(self) -> bool:
        """Return ``True`` if a remote backend or transport is configured."""

        return self._transport is not None or self._openai is not None
