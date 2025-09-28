"""Midpoint scanning between two synastry charts."""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, pi
from typing import Iterable, Mapping, Sequence

from astroengine.core.rel_plus.composite import ChartPositions, circular_midpoint
from astroengine.synastry.policy import MidpointPolicy, family_for_body
from astroengine.utils.angles import delta_angle

__all__ = [
    "MidpointHit",
    "MidpointHotspot",
    "OverlayMarker",
    "MidpointScanResult",
    "scan_midpoints",
]


@dataclass(frozen=True)
class MidpointHit:
    """Represents a single probe aligning with a source midpoint."""

    src_a: str
    src_b: str
    midpoint_lon: float
    probe_chart: str
    probe_body: str
    offset: float
    orb: float
    severity: float
    score: float

    def to_dict(self) -> dict[str, float | str]:
        return {
            "srcA": self.src_a,
            "srcB": self.src_b,
            "mid_lon": self.midpoint_lon,
            "probeChart": self.probe_chart,
            "probeBody": self.probe_body,
            "offset": self.offset,
            "orb": self.orb,
            "severity": self.severity,
            "score": self.score,
        }


@dataclass(frozen=True)
class HotspotProbe:
    probe_chart: str
    probe_body: str
    severity: float
    score: float
    offset: float

    def to_dict(self) -> dict[str, float | str]:
        return {
            "probeChart": self.probe_chart,
            "probeBody": self.probe_body,
            "severity": self.severity,
            "score": self.score,
            "offset": self.offset,
        }


@dataclass(frozen=True)
class MidpointHotspot:
    src_a: str
    src_b: str
    midpoint_lon: float
    top_probes: Sequence[HotspotProbe]
    summary_score: float
    summary_score_a: float
    summary_score_b: float

    def to_dict(self) -> dict[str, object]:
        return {
            "srcA": self.src_a,
            "srcB": self.src_b,
            "mid_lon": self.midpoint_lon,
            "top_probes": [probe.to_dict() for probe in self.top_probes],
            "summary_score": self.summary_score,
            "summary_score_a": self.summary_score_a,
            "summary_score_b": self.summary_score_b,
        }


@dataclass(frozen=True)
class OverlayMarker:
    lon: float
    label: str
    top_probe: str | None

    def to_dict(self) -> dict[str, object | None]:
        return {
            "lon": self.lon,
            "label": self.label,
            "topProbe": self.top_probe,
        }


@dataclass(frozen=True)
class MidpointScanResult:
    midpoint_hits: Sequence[MidpointHit]
    hotspots: Sequence[MidpointHotspot]
    overlay_markers: Sequence[OverlayMarker]

    def to_dict(self) -> dict[str, object]:
        return {
            "midpoint_hits": [hit.to_dict() for hit in self.midpoint_hits],
            "hotspots": [hotspot.to_dict() for hotspot in self.hotspots],
            "overlay": {
                "markers": [marker.to_dict() for marker in self.overlay_markers]
            },
        }


def _angle_offset(probe_lon: float, midpoint_lon: float, probe_body: str) -> float:
    """Return the effective absolute offset for ``probe_body``."""

    base = abs(delta_angle(midpoint_lon, probe_lon))
    family = family_for_body(probe_body)
    name_key = probe_body.lower()
    # Treat node axis symmetrically (Node vs anti-node) using nearest end
    if family == "points" and "node" in name_key:
        alternate = abs(delta_angle(midpoint_lon, (probe_lon + 180.0) % 360.0))
        return min(base, alternate)
    return base


def _severity(offset: float, orb: float, gamma: float) -> float:
    if orb <= 0.0:
        return 1.0 if offset <= 0.0 else 0.0
    x = min(1.0, max(0.0, offset / orb))
    value = 0.5 * (1.0 + cos(pi * x)) if x < 1.0 else 0.0
    return float(value**gamma)


def _normalize_positions(positions: ChartPositions) -> Mapping[str, float]:
    normalized: dict[str, float] = {}
    for key, pos in positions.items():
        name = str(key)
        if hasattr(pos, "lon"):
            lon = float(getattr(pos, "lon"))
        elif hasattr(pos, "longitude"):
            lon = float(getattr(pos, "longitude"))
        else:
            raise AttributeError(f"Unsupported position payload for {name!r}")
        normalized[name] = lon % 360.0
    return normalized


def _family_priority(name: str) -> int:
    family = family_for_body(name)
    priority_map = {
        "luminary": 0,
        "personal": 1,
        "social": 2,
        "outer": 3,
        "points": 4,
    }
    return priority_map.get(family, 5)


def _iter_source_pairs(
    names_a: Sequence[str],
    names_b: Sequence[str],
    *,
    include_intra: bool,
) -> Iterable[tuple[str, str, str]]:
    for src_a in names_a:
        for src_b in names_b:
            yield (src_a, src_b, "A:B")
    if include_intra:
        for idx, src_a in enumerate(names_a):
            for src_b in names_a[idx + 1 :]:
                yield (src_a, src_b, "A:A")
        for idx, src_a in enumerate(names_b):
            for src_b in names_b[idx + 1 :]:
                yield (src_a, src_b, "B:B")


def scan_midpoints(
    positions_a: ChartPositions,
    positions_b: ChartPositions,
    *,
    policy: MidpointPolicy | None = None,
    top_k: int = 3,
    min_severity: float = 0.0,
    include_intra: bool = False,
) -> MidpointScanResult:
    """Return midpoint hits, hotspots, and overlay markers for two charts."""

    if top_k <= 0:
        raise ValueError("top_k must be positive")
    if min_severity < 0.0:
        raise ValueError("min_severity must be non-negative")

    policy = policy or MidpointPolicy()
    lon_a = _normalize_positions(positions_a)
    lon_b = _normalize_positions(positions_b)

    names_a = sorted(lon_a)
    names_b = sorted(lon_b)

    probes: list[tuple[str, str, float]] = []
    for name in names_a:
        probes.append(("A", name, lon_a[name]))
    for name in names_b:
        probes.append(("B", name, lon_b[name]))

    probe_orbs = {
        (chart, body): policy.effective_orb(body) for chart, body, _ in probes
    }
    probe_weights = {
        (chart, body): policy.probe_weight(body) for chart, body, _ in probes
    }

    source_weight_cache = {
        name: policy.source_weight(name) for name in set(names_a + names_b)
    }

    hits: list[MidpointHit] = []
    bucket: dict[tuple[str, str, str], list[MidpointHit]] = {}

    for src_a, src_b, pair_type in _iter_source_pairs(
        names_a, names_b, include_intra=include_intra
    ):
        if pair_type == "A:B":
            lon_mid = circular_midpoint(lon_a[src_a], lon_b[src_b])
        elif pair_type == "A:A":
            lon_mid = circular_midpoint(lon_a[src_a], lon_a[src_b])
        else:
            lon_mid = circular_midpoint(lon_b[src_a], lon_b[src_b])

        weight_a = source_weight_cache[src_a]
        weight_b = source_weight_cache[src_b]

        for probe_chart, probe_body, probe_lon in probes:
            orb = probe_orbs[(probe_chart, probe_body)]
            offset = _angle_offset(probe_lon, lon_mid, probe_body)
            if offset > orb:
                continue
            severity = _severity(offset, orb, policy.severity_gamma)
            if severity < min_severity:
                continue
            score = severity * probe_weights[(probe_chart, probe_body)] * weight_a * weight_b
            hit = MidpointHit(
                src_a=src_a,
                src_b=src_b,
                midpoint_lon=lon_mid,
                probe_chart=probe_chart,
                probe_body=probe_body,
                offset=offset,
                orb=orb,
                severity=severity,
                score=score,
            )
            hits.append(hit)
            bucket.setdefault((pair_type, src_a, src_b), []).append(hit)

    hits.sort(
        key=lambda h: (
            h.src_a,
            h.src_b,
            -h.severity,
            h.offset,
            _family_priority(h.probe_body),
            h.probe_chart,
            h.probe_body,
        )
    )

    hotspots: list[MidpointHotspot] = []
    markers: list[OverlayMarker] = []

    for (pair_type, src_a, src_b), pair_hits in sorted(bucket.items()):
        ordered = sorted(
            pair_hits,
            key=lambda h: (
                -h.severity,
                h.offset,
                _family_priority(h.probe_body),
                h.probe_chart,
                h.probe_body,
            ),
        )
        top = ordered[:top_k]
        summary = max((hit.score for hit in ordered), default=0.0)
        summary_a = max((hit.score for hit in ordered if hit.probe_chart == "A"), default=0.0)
        summary_b = max((hit.score for hit in ordered if hit.probe_chart == "B"), default=0.0)
        hotspot = MidpointHotspot(
            src_a=src_a,
            src_b=src_b,
            midpoint_lon=ordered[0].midpoint_lon,
            top_probes=[
                HotspotProbe(
                    probe_chart=h.probe_chart,
                    probe_body=h.probe_body,
                    severity=h.severity,
                    score=h.score,
                    offset=h.offset,
                )
                for h in top
            ],
            summary_score=summary,
            summary_score_a=summary_a,
            summary_score_b=summary_b,
        )
        hotspots.append(hotspot)
        top_probe = top[0] if top else None
        label_suffix = {
            "A:B": "",
            "A:A": " (A)",
            "B:B": " (B)",
        }.get(pair_type, "")
        marker = OverlayMarker(
            lon=ordered[0].midpoint_lon,
            label=f"{src_a}+{src_b}{label_suffix}",
            top_probe=f"{top_probe.probe_chart}.{top_probe.probe_body}" if top_probe else None,
        )
        markers.append(marker)

    hotspots.sort(key=lambda h: (-(h.summary_score), h.src_a, h.src_b))
    markers.sort(key=lambda m: m.lon)

    return MidpointScanResult(
        midpoint_hits=hits,
        hotspots=hotspots,
        overlay_markers=markers,
    )

