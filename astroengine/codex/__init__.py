"""Codex helpers for exploring the AstroEngine module registry."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from .. import __version__ as _PACKAGE_VERSION
from ..infrastructure.paths import get_paths
from ..modules import DEFAULT_REGISTRY, AstroRegistry, bootstrap_default_registry

__all__ = [
    "CodexNode",
    "UnknownCodexPath",
    "describe_path",
    "get_registry",
    "registry_snapshot",
    "resolved_files",
    "MCPManifest",
    "MCPServerDescriptor",
    "MCPToolDescriptor",
    "codex_mcp_server",
    "common_mcp_servers",
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


@dataclass(frozen=True)
class MCPToolDescriptor:
    """Describe a codex helper exposed via the Model Context Protocol."""

    name: str
    description: str
    input_schema: Mapping[str, object]
    output_schema: Mapping[str, object]
    metadata: Mapping[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable representation of the tool descriptor."""

        payload: dict[str, object] = {
            "name": self.name,
            "description": self.description,
            "inputSchema": dict(self.input_schema),
            "outputSchema": dict(self.output_schema),
        }
        if self.metadata:
            payload["metadata"] = dict(self.metadata)
        return payload


@dataclass(frozen=True)
class MCPManifest:
    """Manifest describing the codex as an MCP-compatible server."""

    name: str
    version: str
    description: str
    tools: Sequence[MCPToolDescriptor]
    resources: Mapping[str, object]
    metadata: Mapping[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable manifest."""

        payload: dict[str, object] = {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "tools": [tool.as_dict() for tool in self.tools],
            "resources": dict(self.resources),
        }
        if self.metadata:
            payload["metadata"] = dict(self.metadata)
        return payload


@dataclass(frozen=True)
class MCPServerDescriptor:
    """Describe an external MCP server that complements the codex."""

    name: str
    description: str
    transport: str
    configuration: Mapping[str, object]
    metadata: Mapping[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable server descriptor."""

        payload: dict[str, object] = {
            "name": self.name,
            "description": self.description,
            "transport": self.transport,
            "configuration": dict(self.configuration),
        }
        if self.metadata:
            payload["metadata"] = dict(self.metadata)
        return payload


def codex_mcp_server(*, refresh: bool = False) -> MCPManifest:
    """Return an MCP manifest for exposing the codex registry helpers."""

    registry = get_registry(refresh=refresh)
    snapshot = registry.as_dict()
    documentation_paths = [
        str(path)
        for path in resolved_files(
            ["developer_platform", "codex", "access", "python"],
            registry=registry,
        )
    ]
    documentation_paths.sort()

    tools = (
        MCPToolDescriptor(
            name="registry_snapshot",
            description="Return the module hierarchy snapshot used by the codex.",
            input_schema={
                "type": "object",
                "properties": {
                    "refresh": {
                        "type": "boolean",
                        "description": "Rebuild the registry from source definitions before returning the snapshot.",
                        "default": False,
                    }
                },
                "additionalProperties": False,
            },
            output_schema={
                "type": "object",
                "description": "Mapping of modules, submodules, channels, and subchannels.",
            },
            metadata={"python": "astroengine.codex.registry_snapshot"},
        ),
        MCPToolDescriptor(
            name="describe_path",
            description="Resolve metadata for a specific module/submodule/channel/subchannel path.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Registry path segments expressed as module/submodule/channel/subchannel.",
                    },
                    "refresh": {
                        "type": "boolean",
                        "description": "Rebuild the registry before resolving the path.",
                        "default": False,
                    },
                },
                "required": ["path"],
                "additionalProperties": False,
            },
            output_schema={
                "type": "object",
                "description": "Metadata and payload describing the requested registry node.",
            },
            metadata={"python": "astroengine.codex.describe_path"},
        ),
        MCPToolDescriptor(
            name="resolved_files",
            description="Resolve filesystem references associated with a registry path.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Registry path segments expressed as module/submodule/channel/subchannel.",
                    },
                    "refresh": {
                        "type": "boolean",
                        "description": "Rebuild the registry before resolving references.",
                        "default": False,
                    },
                },
                "required": ["path"],
                "additionalProperties": False,
            },
            output_schema={
                "type": "array",
                "items": {
                    "type": "string",
                    "description": "Absolute filesystem path to a documentation or dataset resource.",
                },
            },
            metadata={"python": "astroengine.codex.resolved_files"},
        ),
    )

    resources: dict[str, object] = {
        "registry": {
            "kind": "registry",
            "description": "Authoritative registry snapshot sourced from the AstroEngine repository.",
            "data": snapshot,
        }
    }
    if documentation_paths:
        resources["documentation"] = {
            "kind": "filesystem",
            "description": "Documentation files referenced by the codex helper payloads.",
            "paths": documentation_paths,
        }

    metadata: dict[str, object] = {
        "documentation": documentation_paths,
        "module": "developer_platform.codex",
    }

    return MCPManifest(
        name="astroengine-codex",
        version=_PACKAGE_VERSION,
        description=(
            "Read-only registry manifest derived from AstroEngine modules, "
            "suitable for serving via the Model Context Protocol."
        ),
        tools=tools,
        resources=resources,
        metadata=metadata,
    )


def common_mcp_servers() -> tuple[MCPServerDescriptor, ...]:
    """Return curated MCP servers that complement the codex manifest."""

    paths = get_paths()
    project_root = paths.project_root

    datasets_root = project_root / "datasets"
    solafire_root = datasets_root / "solarfire"
    swisseph_root = datasets_root / "swisseph_stub"
    docs_root = project_root / "docs"
    rulesets_root = project_root / "rulesets"

    servers = [
        MCPServerDescriptor(
            name="astroengine-datasets",
            description=(
                "Expose the curated astrology datasets (SolarFire exports and Swiss Ephemeris "
                "stubs) via a filesystem MCP server for data-backed analysis."
            ),
            transport="filesystem",
            configuration={"root": str(datasets_root)},
            metadata={
                "datasets": [str(solafire_root), str(swisseph_root)],
                "documentation": ["datasets/README.md"] if (datasets_root / "README.md").exists() else [],
            },
        ),
        MCPServerDescriptor(
            name="astroengine-docs",
            description=(
                "Serve the AstroEngine documentation tree so MCP clients can cross-reference "
                "run instructions and module narratives."
            ),
            transport="filesystem",
            configuration={"root": str(docs_root)},
            metadata={
                "highlights": [
                    "docs/module/developer_platform/codex.md",
                    "docs/module/developer_platform/cli.md",
                ]
            },
        ),
        MCPServerDescriptor(
            name="astroengine-rulesets",
            description=(
                "Expose rulepack definitions that drive transit and interpretation workflows "
                "for downstream MCP tools."
            ),
            transport="filesystem",
            configuration={"root": str(rulesets_root)},
            metadata={"channels": ["rulesets/transit"]},
        ),
    ]

    return tuple(servers)
