"""Local narrative backends compatible with :class:`GPTNarrativeClient`."""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

LOG = logging.getLogger(__name__)

__all__ = [
    "BackendFactory",
    "LocalNarrativeClient",
    "register_backend",
    "unregister_backend",
    "get_backend",
    "available_backends",
    "LocalBackendUnavailable",
]

BackendFactory = Callable[[Mapping[str, Any]], Callable[..., str]]


class LocalBackendUnavailable(RuntimeError):
    """Raised when a requested local backend cannot be instantiated."""


_BACKENDS: dict[str, BackendFactory] = {}


def register_backend(name: str, factory: BackendFactory, *, replace: bool = False) -> None:
    """Register ``factory`` under ``name`` for later use."""

    if name in _BACKENDS and not replace:
        raise ValueError(f"Backend {name!r} is already registered")
    _BACKENDS[name] = factory


def unregister_backend(name: str) -> None:
    """Remove a backend from the registry if it exists."""

    _BACKENDS.pop(name, None)


def get_backend(name: str) -> BackendFactory | None:
    """Return the registered backend factory for ``name`` when available."""

    return _BACKENDS.get(name)


def available_backends() -> tuple[str, ...]:
    """Return a tuple of registered backend identifiers."""

    return tuple(sorted(_BACKENDS))


def _normalize_options(options: Mapping[str, Any] | None) -> dict[str, Any]:
    data = dict(options or {})
    for key, value in list(data.items()):
        if isinstance(value, str):
            lowered = value.lower()
            if lowered in {"true", "false"}:
                data[key] = lowered == "true"
            else:
                try:
                    data[key] = int(value)
                except ValueError:
                    try:
                        data[key] = float(value)
                    except ValueError:
                        data[key] = value
    return data


def _load_options_from_env(env_var: str) -> dict[str, Any]:
    raw = os.getenv(env_var)
    if not raw:
        return {}
    try:
        if raw.strip().startswith("{"):
            payload = json.loads(raw)
            if isinstance(payload, Mapping):
                return dict(payload)
            LOG.warning("%s did not contain a JSON object", env_var)
            return {}
    except json.JSONDecodeError as exc:
        LOG.warning("Failed to parse %s: %s", env_var, exc)
        return {}
    options: dict[str, Any] = {}
    for chunk in raw.split(","):
        key, sep, value = chunk.partition("=")
        if not sep:
            continue
        options[key.strip()] = value.strip()
    return _normalize_options(options)


@dataclass(slots=True)
class LocalNarrativeClient:
    """Adapter for offline LLM backends."""

    backend: str | None = None
    options: Mapping[str, Any] | None = None
    adapter: Callable[..., str] | None = None
    allow_stub: bool = True

    def __post_init__(self) -> None:
        if self.adapter is not None:
            self._callable = self.adapter
        elif self.backend:
            factory = get_backend(self.backend)
            if factory is None:
                if not self.allow_stub:
                    raise LocalBackendUnavailable(
                        f"Backend {self.backend!r} is not registered"
                    )
                LOG.warning("Local backend '%s' is not registered", self.backend)
                self._callable = None
            else:
                opts = _normalize_options(self.options)
                try:
                    self._callable = factory(opts)
                except Exception as exc:  # pragma: no cover - runtime failures vary
                    if not self.allow_stub:
                        raise LocalBackendUnavailable(str(exc)) from exc
                    LOG.exception("Failed to instantiate local backend '%s'", self.backend)
                    self._callable = None
        else:
            if not self.allow_stub:
                raise LocalBackendUnavailable("No local backend configured")
            self._callable = None

    @property
    def available(self) -> bool:
        """Return ``True`` when a callable adapter is ready."""

        return callable(getattr(self, "_callable", None))

    def summarize(self, prompt: str, *, temperature: float = 0.2) -> str:
        """Return the adapter result for ``prompt``."""

        if not self.available:
            raise LocalBackendUnavailable("No local backend available")

        adapter = self._callable  # type: ignore[attr-defined]
        kwargs = _normalize_options(self.options)
        kwargs.setdefault("temperature", temperature)
        if self.backend and "model" not in kwargs:
            kwargs["model"] = self.backend

        try:
            return str(adapter(prompt, **kwargs)).strip()
        except TypeError:
            return str(adapter(prompt, temperature)).strip()  # type: ignore[call-arg]

    @classmethod
    def from_env(cls, *, allow_stub: bool = True) -> LocalNarrativeClient:
        """Instantiate using ``ASTROENGINE_LOCAL_MODEL`` configuration."""

        backend = os.getenv("ASTROENGINE_LOCAL_MODEL")
        options = _load_options_from_env("ASTROENGINE_LOCAL_MODEL_OPTIONS")
        if backend:
            return cls(backend=backend, options=options, allow_stub=allow_stub)
        return cls(options=options, allow_stub=allow_stub)


def _register_builtin_backends() -> None:
    try:  # pragma: no cover - optional dependency
        from llama_cpp import Llama  # type: ignore
    except Exception:
        return

    def factory(options: Mapping[str, Any]) -> Callable[..., str]:
        model_path = options.get("model_path") or options.get("model")
        if not model_path:
            raise LocalBackendUnavailable("llama.cpp backend requires 'model_path'")
        context = int(options.get("n_ctx", 2048))
        n_gpu_layers = int(options.get("n_gpu_layers", 0))
        llm = Llama(
            model_path=str(model_path),
            n_ctx=context,
            n_gpu_layers=n_gpu_layers,
            logits_all=False,
        )

        def adapter(
            prompt: str,
            *,
            temperature: float = 0.2,
            **_: Any,
        ) -> str:
            response = llm.create_chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
            )
            choices = response.get("choices", []) if isinstance(response, Mapping) else []
            if choices:
                message = choices[0].get("message")
                if isinstance(message, Mapping):
                    return str(message.get("content", "")).strip()
            return ""

        return adapter

    register_backend("llama.cpp", factory, replace=True)


_register_builtin_backends()

