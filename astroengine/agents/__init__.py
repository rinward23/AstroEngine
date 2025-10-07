"""Agent-facing helpers for orchestrating AstroEngine workflows.

The :mod:`astroengine.agents` package exposes a lightweight SDK that wraps the
existing runtime modules without duplicating implementation logic.  It allows
automation agents (for example, Solar Fire import monitors or notification
workers) to interrogate the registry hierarchy, trigger scan entrypoints, and
construct structured context payloads that remain anchored to the
SolarFire-derived datasets shipped with the repository.

Every value returned by this module is derived from the underlying registry or
scan outputs; no synthetic astrology data is introduced.  Callers can trace the
origin of events through the ``datasets`` metadata captured during
``AgentSDK.build_context``.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Callable, Iterable, Mapping, MutableMapping, Sequence

from ..codex import describe_path as _codex_describe_path
from ..codex import resolved_files as _codex_resolved_files
from ..modules import AstroRegistry, DEFAULT_REGISTRY
from ..app_api import run_scan_or_raise

__all__ = ["AgentSDK", "AgentEvent", "AgentScanResult", "AgentSDKError"]


class AgentSDKError(RuntimeError):
    """Raised when agent helpers cannot normalise runtime data."""


@dataclass(frozen=True, slots=True)
class AgentEvent:
    """Normalised event representation exposed to orchestration agents."""

    timestamp: str
    """ISO-8601 timestamp in UTC."""

    moving: str
    """Moving body identifier (e.g., ``"Mars"``)."""

    target: str
    """Target body or chart identifier."""

    aspect: str | None
    """Aspect name (``"conjunction"``, ``"square"`` …) or ``None`` when absent."""

    orb: float | None
    """Orb in degrees when supplied by the scan result."""

    applying: bool | None
    """``True`` for applying contacts, ``False`` for separating, ``None`` when unknown."""

    score: float | None
    """Composite score derived from profile/ruleset weighting."""

    metadata: Mapping[str, Any]
    """Supplementary metadata copied verbatim from the originating event."""

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "timestamp": self.timestamp,
            "moving": self.moving,
            "target": self.target,
            "aspect": self.aspect,
            "orb": self.orb,
            "applying": self.applying,
            "score": self.score,
        }
        if self.metadata:
            data["metadata"] = dict(self.metadata)
        return data


@dataclass(frozen=True, slots=True)
class AgentScanResult:
    """Container returned by :meth:`AgentSDK.scan_transits`."""

    events: tuple[AgentEvent, ...]
    raw_events: tuple[Mapping[str, Any], ...]
    entrypoint: tuple[str, str] | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable snapshot of the scan result."""

        return {
            "events": [event.to_dict() for event in self.events],
            "raw_events": [dict(evt) for evt in self.raw_events],
            "entrypoint": self.entrypoint,
        }


class AgentSDK:
    """High-level facade that keeps agent tooling aligned with runtime modules."""

    def __init__(
        self,
        *,
        registry: AstroRegistry | None = None,
        scan_runner: Callable[..., Any] | None = None,
    ) -> None:
        self._registry = registry or DEFAULT_REGISTRY
        self._scan_runner: Callable[..., Any] = scan_runner or run_scan_or_raise

    # ------------------------------------------------------------------
    # Registry helpers

    @property
    def registry(self) -> AstroRegistry:
        """Return the registry backing the SDK."""

        return self._registry

    def registry_snapshot(self) -> dict[str, Mapping[str, object]]:
        """Return the module → submodule snapshot for discovery tooling."""

        return self._registry.as_dict()

    def describe_path(self, path: Sequence[str] | None = None) -> Mapping[str, Any]:
        """Describe a registry element using the codex helper."""

        node = _codex_describe_path(path or [], registry=self._registry)
        return node.as_dict()

    def resolved_files(self, path: Sequence[str] | None = None) -> list[str]:
        """Resolve documentation/dataset references for ``path``."""

        return [str(p) for p in _codex_resolved_files(path or [], registry=self._registry)]

    # ------------------------------------------------------------------
    # Scan orchestration

    def scan_transits(
        self,
        *,
        start_utc: str,
        end_utc: str,
        moving: Iterable[str],
        targets: Iterable[str],
        include_entrypoint: bool = True,
        **kwargs: Any,
    ) -> AgentScanResult:
        """Execute a transit scan using the configured runner.

        Parameters
        ----------
        start_utc, end_utc:
            ISO-8601 timestamps delimiting the scan window.
        moving, targets:
            Collections of body identifiers to scan.
        include_entrypoint:
            When ``True`` the originating module/function tuple is captured.
        **kwargs:
            Additional keyword arguments forwarded to the scan runner (e.g.,
            ``provider``, ``profile_id``, ``step_minutes``).
        """

        call_kwargs: MutableMapping[str, Any] = {
            "start_utc": start_utc,
            "end_utc": end_utc,
            "moving": list(moving),
            "targets": list(targets),
        }
        call_kwargs.update({k: v for k, v in kwargs.items() if v is not None})
        call_kwargs["return_used_entrypoint"] = bool(include_entrypoint)

        result = self._scan_runner(**call_kwargs)
        if include_entrypoint:
            raw_events, entrypoint = result
        else:
            raw_events, entrypoint = result, None

        normalised = tuple(self._ensure_mapping(event) for event in raw_events)
        agent_events = tuple(self._coerce_agent_event(event) for event in normalised)
        return AgentScanResult(agent_events, normalised, entrypoint)

    def build_context(self, result: AgentScanResult) -> dict[str, Any]:
        """Construct a summarised payload suitable for LLM/agent consumption."""

        events_payload = [event.to_dict() for event in result.events]
        aspect_counter: Counter[str] = Counter(
            event.aspect for event in result.events if event.aspect
        )
        moving_counter: Counter[str] = Counter(event.moving for event in result.events)
        dataset_refs = sorted(self._extract_dataset_references(result))
        profile_ids = sorted(self._collect_meta_field(result, "profile_id"))
        natal_ids = sorted(self._collect_meta_field(result, "natal_id"))

        summary = {
            "count": len(result.events),
            "by_aspect": dict(aspect_counter),
            "by_moving": dict(moving_counter),
            "profile_ids": profile_ids,
            "natal_ids": natal_ids,
        }
        return {
            "entrypoint": result.entrypoint,
            "events": events_payload,
            "datasets": dataset_refs,
            "summary": summary,
            "raw_events": [dict(evt) for evt in result.raw_events],
        }

    # ------------------------------------------------------------------
    # Normalisation helpers

    def _ensure_mapping(self, event: Any) -> Mapping[str, Any]:
        if isinstance(event, Mapping):
            return dict(event)
        if is_dataclass(event):
            return asdict(event)
        if hasattr(event, "__dict__"):
            return dict(vars(event))
        raise AgentSDKError(f"Unsupported event payload: {type(event)!r}")

    def _coerce_agent_event(self, event: Mapping[str, Any]) -> AgentEvent:
        data = dict(event)
        timestamp = self._extract_timestamp(data)
        moving = self._extract_moving(data)
        target = self._extract_target(data)
        aspect = self._extract_aspect(data)
        orb, orb_metadata = self._extract_orb(data)
        applying = self._extract_applying(data)
        score = self._extract_score(data)

        metadata: dict[str, Any] = {}
        for key, value in data.items():
            if key not in {
                "ts",
                "timestamp",
                "when",
                "when_iso",
                "time",
                "moving",
                "body",
                "a",
                "target",
                "b",
                "aspect",
                "kind",
                "orb",
                "orb_abs",
                "orb_abs_deg",
                "orb_allow",
                "orb_limit",
                "applying",
                "applying_or_separating",
                "score",
                "severity",
                "angle_deg",
                "family",
            }:
                metadata[key] = value
        metadata.update(orb_metadata)
        return AgentEvent(
            timestamp=timestamp,
            moving=moving,
            target=target,
            aspect=aspect,
            orb=orb,
            applying=applying,
            score=score,
            metadata=metadata,
        )

    @staticmethod
    def _extract_timestamp(data: Mapping[str, Any]) -> str:
        for key in ("ts", "timestamp", "when", "when_iso", "time"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        raise AgentSDKError("Event payload missing timestamp field")

    @staticmethod
    def _extract_moving(data: Mapping[str, Any]) -> str:
        for key in ("moving", "body", "a"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        raise AgentSDKError("Event payload missing moving body")

    @staticmethod
    def _extract_target(data: Mapping[str, Any]) -> str:
        for key in ("target", "b"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        raise AgentSDKError("Event payload missing target body")

    @staticmethod
    def _extract_aspect(data: Mapping[str, Any]) -> str | None:
        aspect = data.get("aspect")
        if isinstance(aspect, str) and aspect.strip():
            return aspect.strip()
        kind = data.get("kind")
        if isinstance(kind, str) and kind.strip():
            cleaned = kind.strip().lower()
            if cleaned.startswith("aspect_"):
                return cleaned.split("aspect_", 1)[1]
        angle = data.get("angle_deg")
        if isinstance(angle, (int, float)):
            mapping = {
                0.0: "conjunction",
                60.0: "sextile",
                90.0: "square",
                120.0: "trine",
                180.0: "opposition",
            }
            for deg, name in mapping.items():
                if abs(float(angle) - deg) < 1e-6:
                    return name
        return None

    @staticmethod
    def _extract_orb(data: Mapping[str, Any]) -> tuple[float | None, dict[str, Any]]:
        orb_value = data.get("orb")
        if isinstance(orb_value, (int, float)):
            return float(orb_value), {}
        orb_abs = data.get("orb_abs")
        if isinstance(orb_abs, (int, float)):
            return float(orb_abs), {"orb_is_absolute": True}
        orb_limit = data.get("orb_limit")
        if isinstance(orb_limit, (int, float)):
            return float(orb_limit), {"orb_is_limit": True}
        return None, {}

    @staticmethod
    def _extract_applying(data: Mapping[str, Any]) -> bool | None:
        applying = data.get("applying")
        if isinstance(applying, bool):
            return applying
        stage = data.get("applying_or_separating")
        if isinstance(stage, str):
            cleaned = stage.strip().lower()
            if cleaned in {"applying", "separating"}:
                return cleaned == "applying"
        return None

    @staticmethod
    def _extract_score(data: Mapping[str, Any]) -> float | None:
        for key in ("score", "severity"):
            value = data.get(key)
            if isinstance(value, (int, float)):
                return float(value)
        return None

    # ------------------------------------------------------------------
    # Metadata extraction helpers

    @staticmethod
    def _collect_meta_field(result: AgentScanResult, field: str) -> set[str]:
        values: set[str] = set()
        for event in result.events:
            meta_value = event.metadata.get(field)
            if isinstance(meta_value, str) and meta_value.strip():
                values.add(meta_value.strip())
        return values

    @staticmethod
    def _extract_dataset_references(result: AgentScanResult) -> set[str]:
        keys = {"dataset", "dataset_path", "dataset_hash", "source", "provenance"}
        references: set[str] = set()
        for event in result.events:
            for key in keys:
                value = event.metadata.get(key)
                if isinstance(value, str) and value.strip():
                    references.add(value.strip())
        return references


def events_to_agent_events(events: Iterable[Mapping[str, Any]]) -> list[AgentEvent]:
    """Utility helper mirroring :func:`events_from_any` for agent payloads."""

    sdk = AgentSDK()
    return [sdk._coerce_agent_event(event) for event in events]

