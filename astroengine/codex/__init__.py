"""Codex helpers for exploring the AstroEngine module registry."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from ..infrastructure.paths import get_paths
from ..modules import DEFAULT_REGISTRY, AstroRegistry, bootstrap_default_registry

__all__ = [
    "CodexNode",
    "UnknownCodexPath",
    "describe_path",
    "get_registry",
    "registry_snapshot",
    "resolved_files",
]


@dataclass(frozen=True)
class CodexNode:
    """Resolved element within the registry hierarchy."""

    kind: str
    name: str | None
    metadata: Mapping[str, object]
    payload: Mapping[str, object] | None = None
    children: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable representation of the node."""

        data: dict[str, object] = {
            "kind": self.kind,
            "name": self.name,
            "metadata": dict(self.metadata),
        }
        if self.payload is not None:
            data["payload"] = dict(self.payload)
        if self.children:
            data["children"] = list(self.children)
        return data


class UnknownCodexPath(KeyError):
    """Raised when a path cannot be resolved within the registry."""


def get_registry(*, refresh: bool = False) -> AstroRegistry:
    """Return the registry used by the codex helpers.

    Parameters
    ----------
    refresh:
        When ``True`` a fresh registry is constructed via
        :func:`bootstrap_default_registry`. Otherwise the cached
        :data:`~astroengine.modules.DEFAULT_REGISTRY` snapshot is reused.
    """

    if refresh:
        return bootstrap_default_registry()
    return DEFAULT_REGISTRY


def registry_snapshot(*, refresh: bool = False) -> dict[str, Mapping[str, object]]:
    """Return a serialisable snapshot of the registry hierarchy."""

    return get_registry(refresh=refresh).as_dict()


def describe_path(
    path: Sequence[str] | None = None,
    *,
    registry: AstroRegistry | None = None,
) -> CodexNode:
    """Resolve ``path`` to a registry element.

    The ``path`` is expressed as a sequence of up to four identifiers:
    ``module / submodule / channel / subchannel``. Omitting segments
    returns higher level nodes.
    """

    registry = registry or get_registry()
    segments = list(path or [])
    if not segments:
        return CodexNode(
            kind="registry",
            name=None,
            metadata={"modules": sorted(m.name for m in registry.iter_modules())},
            children=sorted(m.name for m in registry.iter_modules()),
        )

    try:
        module = registry.get_module(segments[0])
    except KeyError as exc:  # pragma: no cover - defensive
        raise UnknownCodexPath(segments) from exc

    if len(segments) == 1:
        return CodexNode(
            kind="module",
            name=module.name,
            metadata=module.metadata,
            children=sorted(module.submodules.keys()),
        )

    try:
        submodule = module.get_submodule(segments[1])
    except KeyError as exc:
        raise UnknownCodexPath(segments) from exc

    if len(segments) == 2:
        return CodexNode(
            kind="submodule",
            name=submodule.name,
            metadata=submodule.metadata,
            children=sorted(submodule.channels.keys()),
        )

    try:
        channel = submodule.get_channel(segments[2])
    except KeyError as exc:
        raise UnknownCodexPath(segments) from exc

    if len(segments) == 3:
        return CodexNode(
            kind="channel",
            name=channel.name,
            metadata=channel.metadata,
            children=sorted(channel.subchannels.keys()),
        )

    try:
        subchannel = channel.get_subchannel(segments[3])
    except KeyError as exc:
        raise UnknownCodexPath(segments) from exc

    data = subchannel.describe()
    payload = data.get("payload") if isinstance(data, dict) else None
    metadata = data if payload is None else {k: v for k, v in data.items() if k != "payload"}
    return CodexNode(
        kind="subchannel",
        name=subchannel.name,
        metadata=metadata,
        payload=payload if isinstance(payload, Mapping) else None,
        children=[],
    )


def _candidate_paths(value: object) -> Iterable[Path]:
    if isinstance(value, str):
        text = value.strip()
        if not text or "://" in text:
            return []
        fragment, _, _ = text.partition("#")
        if not fragment:
            return []
        candidate = Path(fragment)
        paths = get_paths()
        bases = [paths.project_root, paths.package_root]
        # Skip obvious commands like "astroengine scan" which contain spaces
        if " " in fragment and "/" not in fragment:
            return []
        candidates: list[Path] = []
        if candidate.is_absolute() and candidate.exists():
            candidates.append(candidate)
        else:
            for base in bases:
                potential = base / fragment
                if potential.exists():
                    candidates.append(potential)
        return candidates
    if isinstance(value, Mapping):
        results: list[Path] = []
        for nested in value.values():
            results.extend(_candidate_paths(nested))
        return results
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray, str)):
        results: list[Path] = []
        for nested in value:
            results.extend(_candidate_paths(nested))
        return results
    return []


def resolved_files(
    path: Sequence[str] | None = None,
    *,
    registry: AstroRegistry | None = None,
) -> list[Path]:
    """Return filesystem paths referenced by the metadata for ``path``."""

    node = describe_path(path or [], registry=registry)
    data: dict[str, object] = dict(node.metadata)
    if node.payload is not None:
        data.setdefault("payload", node.payload)

    seen: set[Path] = set()
    resolved: list[Path] = []
    for candidate in _candidate_paths(data):
        if candidate not in seen:
            resolved.append(candidate)
            seen.add(candidate)
    return resolved
