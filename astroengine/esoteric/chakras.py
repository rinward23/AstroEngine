"""Chakra correspondences bridging planetary rulers and VCA domains."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import json

from ..infrastructure.paths import profiles_dir
from ..vca.houses import DomainW, HouseSystem, weights_for_body

__all__ = [
    "ChakraCorrespondence",
    "chakra_correspondences",
    "load_chakra_correspondences",
    "chakra_emphasis",
    "chakra_emphasis_for_chart",
]


@dataclass(frozen=True)
class ChakraCorrespondence:
    """Structured chakra correspondences sourced from Tantric literature."""

    id: str
    sanskrit: str
    english: str
    element: str
    planetary_rulers: tuple[str, ...]
    domain_weights: Mapping[str, float]
    notes: str | None = None
    sources: tuple[str, ...] = ()

    def normalized_domains(self) -> dict[str, float]:
        """Return Mind/Body/Spirit weights normalised to unity."""

        total = 0.0
        normalized: dict[str, float] = {}
        for key, value in self.domain_weights.items():
            try:
                weight = float(value)
            except (TypeError, ValueError):
                continue
            if weight <= 0.0:
                continue
            normalized[key.upper()] = normalized.get(key.upper(), 0.0) + weight
            total += weight
        if total <= 0.0:
            return {"MIND": 1.0 / 3.0, "BODY": 1.0 / 3.0, "SPIRIT": 1.0 / 3.0}
        return {key: weight / total for key, weight in normalized.items()}

    def canonical_rulers(self) -> tuple[str, ...]:
        """Return canonicalised planetary ruler identifiers."""

        return tuple(sorted({ruler.strip().lower() for ruler in self.planetary_rulers if ruler}))

    def to_payload(self) -> dict[str, Any]:
        """Return a serialisable representation of the correspondence."""

        return {
            "id": self.id,
            "sanskrit": self.sanskrit,
            "english": self.english,
            "element": self.element,
            "planetary_rulers": list(self.planetary_rulers),
            "domain_weights": dict(self.normalized_domains()),
            "notes": self.notes,
            "sources": list(self.sources),
        }


def _default_dataset_path() -> Path:
    return profiles_dir() / "correspondences" / "chakras.json"


def _coerce_sequence(value: Any) -> tuple[str, ...]:
    if isinstance(value, (list, tuple, set)):
        return tuple(str(item) for item in value if item)
    if value is None:
        return ()
    return (str(value),)


def _load_dataset(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Chakra correspondence dataset must be a JSON object")
    return data


def load_chakra_correspondences(path: str | Path | None = None) -> tuple[ChakraCorrespondence, ...]:
    """Load chakra correspondences from the JSON dataset."""

    dataset_path = Path(path) if path else _default_dataset_path()
    payload = _load_dataset(dataset_path)
    chakras = payload.get("chakras", [])
    if not isinstance(chakras, Sequence):
        raise ValueError("'chakras' must be a sequence of mappings")
    collection: list[ChakraCorrespondence] = []
    global_sources = tuple(str(src) for src in _coerce_sequence(payload.get("sources")))
    for entry in chakras:
        if not isinstance(entry, Mapping):
            continue
        domain_weights = entry.get("domain_weights", {})
        if not isinstance(domain_weights, Mapping):
            domain_weights = {}
        converted_weights: dict[str, float] = {}
        for key, value in domain_weights.items():
            try:
                converted_weights[str(key).upper()] = float(value)
            except (TypeError, ValueError):
                continue
        combined_sources: list[str] = []
        for source in (*global_sources, *_coerce_sequence(entry.get("sources"))):
            if source and source not in combined_sources:
                combined_sources.append(source)
        correspondence = ChakraCorrespondence(
            id=str(entry.get("id", "")),
            sanskrit=str(entry.get("sanskrit", "")),
            english=str(entry.get("english", "")),
            element=str(entry.get("element", "")),
            planetary_rulers=_coerce_sequence(entry.get("planetary_rulers")),
            domain_weights=converted_weights or {"MIND": 1.0 / 3.0, "BODY": 1.0 / 3.0, "SPIRIT": 1.0 / 3.0},
            notes=str(entry.get("notes", "")) if entry.get("notes") else None,
            sources=tuple(combined_sources),
        )
        collection.append(correspondence)
    return tuple(collection)


@lru_cache(maxsize=1)
def chakra_correspondences() -> tuple[ChakraCorrespondence, ...]:
    """Return the cached chakra correspondences dataset."""

    return load_chakra_correspondences()


def _domain_projection(chakra: ChakraCorrespondence, domain: DomainW) -> float:
    weights = chakra.normalized_domains()
    normalized = domain.normalized()
    mapping = {
        "MIND": normalized.Mind,
        "BODY": normalized.Body,
        "SPIRIT": normalized.Spirit,
    }
    return sum(mapping.get(key, 0.0) * weight for key, weight in weights.items())


def chakra_emphasis(
    domain_by_body: Mapping[str, DomainW] | Iterable[tuple[str, DomainW]],
    *,
    dataset: Sequence[ChakraCorrespondence] | None = None,
    weights: Mapping[str, float] | None = None,
) -> dict[str, float]:
    """Compute chakra emphasis scores from planetary Mind/Body/Spirit weights.

    ``domain_by_body`` accepts either a mapping of canonical body identifiers
    (``"sun"``, ``"moon"``, etc.) to :class:`DomainW` weights or an iterable of
    ``(body, DomainW)`` pairs. ``weights`` can optionally scale each body before
    aggregation (e.g., luminaries > outers).
    """

    if isinstance(domain_by_body, Mapping):
        items = domain_by_body.items()
    else:
        items = tuple(domain_by_body)
    lookup: dict[str, DomainW] = {str(key).lower(): value for key, value in items}
    dataset = tuple(dataset) if dataset is not None else chakra_correspondences()
    body_weights = {str(key).lower(): float(value) for key, value in (weights or {}).items()}

    scores: dict[str, float] = {}
    for chakra in dataset:
        total = 0.0
        for ruler in chakra.canonical_rulers():
            domain = lookup.get(ruler)
            if domain is None:
                continue
            factor = body_weights.get(ruler, 1.0)
            if factor <= 0.0:
                continue
            total += _domain_projection(chakra, domain) * factor
        if total > 0.0:
            scores[chakra.id] = total

    if not scores and dataset:
        uniform = 1.0 / len(dataset)
        return {chakra.id: uniform for chakra in dataset}

    total_score = sum(scores.values())
    if total_score <= 0.0:
        return {chakra.id: 0.0 for chakra in dataset}
    return {
        chakra.id: scores.get(chakra.id, 0.0) / total_score
        for chakra in dataset
    }


def chakra_emphasis_for_chart(
    chart: Any,
    *,
    bodies: Iterable[str] | None = None,
    system: str | HouseSystem = HouseSystem.PLACIDUS,
    dataset: Sequence[ChakraCorrespondence] | None = None,
    weights: Mapping[str, float] | None = None,
) -> dict[str, float]:
    """Convenience wrapper that derives chakra emphasis from a natal chart.

    ``bodies`` defaults to every planetary ruler enumerated in the supplied (or
    default) dataset.  House weighting uses :func:`astroengine.vca.houses.weights_for_body`
    to remain aligned with the VCA domain pipeline.
    """

    dataset = tuple(dataset) if dataset is not None else chakra_correspondences()
    if bodies is None:
        unique_bodies = {
            ruler
            for chakra in dataset
            for ruler in chakra.canonical_rulers()
        }
        bodies = sorted(unique_bodies)
    normalized_system = str(system if system is not None else HouseSystem.PLACIDUS).lower()
    domain_map: dict[str, DomainW] = {}
    for body in bodies:
        try:
            domain_map[str(body).lower()] = weights_for_body(
                chart,
                str(body).lower(),
                normalized_system,
            )
        except Exception:
            continue
    return chakra_emphasis(domain_map, dataset=dataset, weights=weights)
