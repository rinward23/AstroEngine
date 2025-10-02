"""GPT-backed narrative helpers with graceful fallbacks."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable, Iterable
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
        base_url: str | None = None,
        transport: Callable[..., str] | None = None,
        allow_stub: bool = True,
    ) -> None:
        self.api_key = api_key
        env_model = os.getenv("ASTROENGINE_OPENAI_MODEL")
        self.model = env_model or model
        self.base_url = (
            base_url
            or os.getenv("ASTROENGINE_OPENAI_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
        )
        self._transport = transport
        self._openai: Any | None = None
        self._client_kind: str | None = None
        if transport is None and api_key:
            errors: list[Exception] = []
            try:  # pragma: no cover - requires optional dependency
                from openai import OpenAI  # type: ignore
            except Exception as exc:  # pragma: no cover
                errors.append(exc)
            else:
                try:
                    client_kwargs: dict[str, Any] = {"api_key": api_key}
                    if self.base_url:
                        client_kwargs["base_url"] = self.base_url
                    self._openai = OpenAI(**client_kwargs)
                except Exception as exc:  # pragma: no cover - instantiation failure
                    errors.append(exc)
                else:
                    self._client_kind = "chat.completions"
            if self._openai is None:
                try:  # pragma: no cover - legacy dependency path
                    import openai as openai_legacy  # type: ignore
                except Exception as exc:  # pragma: no cover
                    errors.append(exc)
                else:
                    self._openai = openai_legacy
                    self._client_kind = "legacy"
                    self._openai.api_key = api_key
                    if self.base_url:
                        setattr(self._openai, "api_base", self.base_url)
            if self._openai is None and errors:
                if not allow_stub:
                    raise errors[-1]
                LOG.warning(
                    "OpenAI client unavailable: %s",
                    "; ".join(str(error) for error in errors),
                )
            elif self._openai is None and not allow_stub:
                raise RuntimeError("OpenAI client unavailable")

    @classmethod
    def from_env(
        cls,
        *,
        model: str = "gpt-3.5-turbo",
        base_url: str | None = None,
        transport: Callable[..., str] | None = None,
    ) -> GPTNarrativeClient:
        api_key = (
            os.getenv("ASTROENGINE_OPENAI_KEY")
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("GITHUB_TOKEN")
        )
        env_model = os.getenv("ASTROENGINE_OPENAI_MODEL")
        env_base_url = (
            os.getenv("ASTROENGINE_OPENAI_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
            or base_url
        )
        return cls(
            api_key,
            model=env_model or model,
            base_url=env_base_url,
            transport=transport,
        )

    def summarize(self, prompt: str, *, temperature: float = 0.2) -> str:
        """Return a summary for ``prompt`` using the configured backend."""

        if self._transport is not None:
            return self._transport(prompt, model=self.model, temperature=temperature)
        if self._openai is None:
            raise RuntimeError("No GPT backend configured")
        if self._client_kind == "chat.completions":
            response = self._openai.chat.completions.create(  # type: ignore[call-arg]
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
            )
            choices = getattr(response, "choices", [])
        else:
            response = self._openai.ChatCompletion.create(  # type: ignore[call-arg]
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
            )
            choices = response.get("choices", [])
        choice = choices[0] if choices else None
        return self._extract_choice_content(choice)

    @property
    def available(self) -> bool:
        """Return ``True`` if a remote backend or transport is configured."""

        return self._transport is not None or self._openai is not None

    @staticmethod
    def _extract_choice_content(choice: Any) -> str:
        if choice is None:
            return ""
        message = getattr(choice, "message", None)
        if message is None and isinstance(choice, dict):
            message = choice.get("message")
        if message is None:
            return ""
        content: Any = getattr(message, "content", None)
        if content is None and isinstance(message, dict):
            content = message.get("content")
        if isinstance(content, Iterable) and not isinstance(content, (str, bytes)):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if text:
                        parts.append(str(text))
                elif item:
                    parts.append(str(item))
            content = "".join(parts)
        return str(content or "").strip()
