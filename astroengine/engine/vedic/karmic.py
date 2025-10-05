"""Karmic indicator calculations for sidereal charts.

This module adds Atmakaraka and Karakamsha Lagna helpers together with
supporting metrics that rely on concrete chart data:

* Chara karaka ordering derived from each planet's degrees within its sign.
* Karakamsha Lagna derived from the Navamsa placement of the Atmakaraka.
* Ishta / Kashta phala scores using distances from exaltation/debilitation.
* High level karma attributions (Sanchita, Prarabdha, Kriyamana).
* Eclipse alignment analysis describing Sun/Rahu and Moon/Ketu separations.

All computations operate on :class:`~astroengine.chart.NatalChart` instances and
only use values provided by the configured Swiss ephemeris adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from ...chart import NatalChart
from ...detectors.ingresses import ZODIAC_SIGNS, sign_index
from ...ephemeris import BodyPosition, SwissEphemerisAdapter
from ...ephemeris.swisseph_adapter import get_swisseph
from .chart import VedicChartContext
from .varga import navamsa_sign

__all__ = [
    "CharaKaraka",
    "KarakamshaLagna",
    "IshtaKashtaResult",
    "KarmaSegment",
    "EclipseAlignment",
    "compute_chara_karakas",
    "karakamsha_lagna",
    "ishta_kashta_phala",
    "karma_attributions",
    "eclipse_alignment_roles",
    "build_karmic_profile",
]


@dataclass(frozen=True)
class CharaKaraka:
    """Represents a single chara karaka designation."""

    role: str
    planet: str
    longitude: float
    degrees_in_sign: float
    sign_index: int
    sign: str

    def to_dict(self) -> dict[str, object]:
        return {
            "role": self.role,
            "planet": self.planet,
            "longitude": self.longitude,
            "degrees_in_sign": self.degrees_in_sign,
            "sign_index": self.sign_index,
            "sign": self.sign,
        }


@dataclass(frozen=True)
class KarakamshaLagna:
    """Navāṁśa placement of the Atmakaraka."""

    sign_index: int
    sign: str
    longitude: float
    pada: int
    atmakaraka: CharaKaraka

    def to_dict(self) -> dict[str, object]:
        return {
            "sign_index": self.sign_index,
            "sign": self.sign,
            "longitude": self.longitude,
            "pada": self.pada,
            "atmakaraka": self.atmakaraka.to_dict(),
        }


@dataclass(frozen=True)
class IshtaKashtaResult:
    """Ishta/Kashta phala scores derived from exaltation proximity."""

    planet: str
    ishta: float
    kashta: float
    distance_exaltation: float
    distance_debilitation: float
    exaltation_longitude: float
    debilitation_longitude: float

    def to_dict(self) -> dict[str, float]:
        return {
            "planet": self.planet,
            "ishta": self.ishta,
            "kashta": self.kashta,
            "distance_exaltation": self.distance_exaltation,
            "distance_debilitation": self.distance_debilitation,
            "exaltation_longitude": self.exaltation_longitude,
            "debilitation_longitude": self.debilitation_longitude,
        }


@dataclass(frozen=True)
class KarmaSegment:
    """Summary score for a karmic segment with contextual notes."""

    segment: str
    score: float
    average_ishta: float
    average_kashta: float
    planets: tuple[str, ...]
    summary: str

    def to_dict(self) -> dict[str, object]:
        return {
            "segment": self.segment,
            "score": self.score,
            "average_ishta": self.average_ishta,
            "average_kashta": self.average_kashta,
            "planets": self.planets,
            "summary": self.summary,
        }


@dataclass(frozen=True)
class EclipseAlignment:
    """Alignment report describing node proximity for luminaries."""

    pair: str
    separation: float
    alignment: float
    nodes_variant: str
    summary: str

    def to_dict(self) -> dict[str, object]:
        return {
            "pair": self.pair,
            "separation": self.separation,
            "alignment": self.alignment,
            "nodes_variant": self.nodes_variant,
            "summary": self.summary,
        }


@dataclass(frozen=True)
class KarmicProfile:
    """Top level container bundling karmic indicators for a chart."""

    karakas: tuple[CharaKaraka, ...]
    karakamsha: KarakamshaLagna
    ishta_kashta: Mapping[str, IshtaKashtaResult]
    karma_segments: Mapping[str, KarmaSegment]
    eclipse_alignments: Mapping[str, EclipseAlignment]

    def to_dict(self) -> dict[str, object]:
        return {
            "karakas": [karaka.to_dict() for karaka in self.karakas],
            "karakamsha": self.karakamsha.to_dict(),
            "ishta_kashta": {
                name: result.to_dict() for name, result in self.ishta_kashta.items()
            },
            "karma_segments": {
                name: segment.to_dict() for name, segment in self.karma_segments.items()
            },
            "eclipse_alignments": {
                name: alignment.to_dict()
                for name, alignment in self.eclipse_alignments.items()
            },
        }


_CHARA_KARAKA_ROLES: tuple[str, ...] = (
    "atmakaraka",
    "amatyakaraka",
    "bhratrukaraka",
    "matrukaraka",
    "putrakaraka",
    "gnatikaraka",
    "darakaraka",
)

_EXALTATION_LONGITUDES: Mapping[str, float] = {
    "Sun": 10.0,
    "Moon": 33.0,
    "Mars": 298.0,
    "Mercury": 165.0,
    "Jupiter": 95.0,
    "Venus": 357.0,
    "Saturn": 200.0,
}

_PLANET_SEQUENCE: Sequence[str] = (
    "Sun",
    "Moon",
    "Mars",
    "Mercury",
    "Jupiter",
    "Venus",
    "Saturn",
)


def _normalize_longitude(longitude: float) -> float:
    return float(longitude) % 360.0


def _degrees_in_sign(longitude: float) -> float:
    return _normalize_longitude(longitude) % 30.0


def _angular_distance(a: float, b: float) -> float:
    diff = (_normalize_longitude(a) - _normalize_longitude(b)) % 360.0
    return diff if diff <= 180.0 else 360.0 - diff


def _debilitation_longitude(exaltation: float) -> float:
    return (exaltation + 180.0) % 360.0


def _collect_candidates(positions: Mapping[str, BodyPosition]) -> list[tuple[str, BodyPosition]]:
    return [
        (name, positions[name])
        for name in _PLANET_SEQUENCE
        if name in positions and positions[name].longitude is not None
    ]


def compute_chara_karakas(chart: NatalChart) -> tuple[CharaKaraka, ...]:
    """Return ordered chara karakas for ``chart``.

    The highest degrees-in-sign becomes the Atmakaraka and the remaining
    planets fill sequential karaka roles. Only classical grahas are
    considered to maintain deterministic ordering regardless of node
    availability in the chart payload.
    """

    candidates = _collect_candidates(chart.positions)
    if not candidates:
        raise ValueError("no classical planets available for chara karaka computation")

    ranked = sorted(
        (
            (
                name,
                position,
                _degrees_in_sign(position.longitude),
                sign_index(position.longitude),
            )
            for name, position in candidates
        ),
        key=lambda item: item[2],
        reverse=True,
    )

    karakas: list[CharaKaraka] = []
    for role, payload in zip(_CHARA_KARAKA_ROLES, ranked):
        name, position, deg_in_sign, sign_idx = payload
        karakas.append(
            CharaKaraka(
                role=role,
                planet=name,
                longitude=_normalize_longitude(position.longitude),
                degrees_in_sign=deg_in_sign,
                sign_index=sign_idx,
                sign=ZODIAC_SIGNS[sign_idx],
            )
        )
    return tuple(karakas)


def karakamsha_lagna(chart: NatalChart) -> KarakamshaLagna:
    """Return the Karakamsha Lagna derived from ``chart``.

    The function locates the Atmakaraka then projects it into the Navāṁśa.
    """

    karakas = compute_chara_karakas(chart)
    atma = next(karaka for karaka in karakas if karaka.role == "atmakaraka")
    sign_idx, longitude, pada = navamsa_sign(atma.longitude)
    return KarakamshaLagna(
        sign_index=sign_idx,
        sign=ZODIAC_SIGNS[sign_idx],
        longitude=longitude,
        pada=pada,
        atmakaraka=atma,
    )


def _score_from_distance(distance: float) -> float:
    """Normalize a distance (0-180) into a 0..1 score."""

    clamped = max(0.0, min(distance, 180.0))
    return 1.0 - (clamped / 180.0)


def ishta_kashta_phala(chart: NatalChart) -> dict[str, IshtaKashtaResult]:
    """Compute Ishta/Kashta metrics for each classical graha."""

    results: dict[str, IshtaKashtaResult] = {}
    for planet in _PLANET_SEQUENCE:
        position = chart.positions.get(planet)
        exaltation = _EXALTATION_LONGITUDES.get(planet)
        if position is None or exaltation is None:
            continue
        debilitation = _debilitation_longitude(exaltation)
        distance_exaltation = _angular_distance(position.longitude, exaltation)
        distance_debilitation = _angular_distance(position.longitude, debilitation)
        ishta_score = _score_from_distance(distance_exaltation)
        kashta_score = _score_from_distance(distance_debilitation)
        results[planet] = IshtaKashtaResult(
            planet=planet,
            ishta=ishta_score,
            kashta=kashta_score,
            distance_exaltation=distance_exaltation,
            distance_debilitation=distance_debilitation,
            exaltation_longitude=exaltation,
            debilitation_longitude=debilitation,
        )
    return results


def _segment_summary(
    segment: str,
    planets: Sequence[str],
    scores: Mapping[str, IshtaKashtaResult],
) -> KarmaSegment:
    available: list[IshtaKashtaResult] = [scores[p] for p in planets if p in scores]
    if not available:
        return KarmaSegment(
            segment=segment,
            score=0.0,
            average_ishta=0.0,
            average_kashta=0.0,
            planets=tuple(planets),
            summary="No planetary data available for this segment.",
        )

    average_ishta = sum(item.ishta for item in available) / len(available)
    average_kashta = sum(item.kashta for item in available) / len(available)
    score = average_ishta - average_kashta

    qualifier = "supportive" if score >= 0 else "challenging"
    summary = (
        f"Average ishta {average_ishta:.3f} vs kashta {average_kashta:.3f} from "
        f"{', '.join(planets)} indicates {qualifier} momentum."
    )
    return KarmaSegment(
        segment=segment,
        score=score,
        average_ishta=average_ishta,
        average_kashta=average_kashta,
        planets=tuple(planets),
        summary=summary,
    )


def karma_attributions(chart: NatalChart) -> dict[str, KarmaSegment]:
    """Derive karma segments using ishta/kashta ratios."""

    scores = ishta_kashta_phala(chart)
    segments = {
        "sanchita": _segment_summary("Sanchita", ("Jupiter", "Saturn"), scores),
        "prarabdha": _segment_summary("Prarabdha", ("Sun", "Moon"), scores),
        "kriyamana": _segment_summary("Kriyamana", ("Mercury", "Venus", "Mars"), scores),
    }
    return segments


def _node_positions(
    adapter: SwissEphemerisAdapter,
    julian_day: float,
    *,
    nodes_variant: str,
) -> tuple[BodyPosition, BodyPosition]:
    node_name = "true_node" if nodes_variant == "true" else "mean_node"
    try:
        swe = get_swisseph()
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency guard
        raise RuntimeError(
            "Swiss Ephemeris is required for karmic node calculations. Install astroengine[ephem]."
        ) from exc
    rahu = adapter.body_position(
        julian_day,
        int(getattr(swe, "TRUE_NODE" if nodes_variant == "true" else "MEAN_NODE")),
        body_name=node_name,
    )
    ketu = adapter.body_position(
        julian_day,
        int(getattr(swe, "TRUE_NODE" if nodes_variant == "true" else "MEAN_NODE")),
        body_name="south_node",
    )
    return rahu, ketu


def eclipse_alignment_roles(context: VedicChartContext) -> dict[str, EclipseAlignment]:
    """Evaluate the karmic eclipse axes for a chart context."""

    chart = context.chart
    nodes_variant = "mean"
    if chart.metadata:
        nodes_variant = str(chart.metadata.get("nodes_variant", "mean")).lower()
    rahu, ketu = _node_positions(context.adapter, chart.julian_day, nodes_variant=nodes_variant)

    results: dict[str, EclipseAlignment] = {}
    sun = chart.positions.get("Sun")
    moon = chart.positions.get("Moon")
    if sun is not None:
        separation = _angular_distance(sun.longitude, rahu.longitude)
        alignment = _score_from_distance(separation)
        summary = (
            f"Sun-Rahu separation of {separation:.3f}° using {nodes_variant} node "
            f"variant yields alignment score {alignment:.3f}."
        )
        results["sun_rahu"] = EclipseAlignment(
            pair="Sun-Rahu",
            separation=separation,
            alignment=alignment,
            nodes_variant=nodes_variant,
            summary=summary,
        )
    if moon is not None:
        separation = _angular_distance(moon.longitude, ketu.longitude)
        alignment = _score_from_distance(separation)
        summary = (
            f"Moon-Ketu separation of {separation:.3f}° using {nodes_variant} node "
            f"variant yields alignment score {alignment:.3f}."
        )
        results["moon_ketu"] = EclipseAlignment(
            pair="Moon-Ketu",
            separation=separation,
            alignment=alignment,
            nodes_variant=nodes_variant,
            summary=summary,
        )
    return results


def build_karmic_profile(context: VedicChartContext) -> KarmicProfile:
    """Construct a full karmic profile for the provided context."""

    karakas = compute_chara_karakas(context.chart)
    karakamsha = karakamsha_lagna(context.chart)
    ishta_kashta = ishta_kashta_phala(context.chart)
    segments = karma_attributions(context.chart)
    eclipse_roles = eclipse_alignment_roles(context)
    return KarmicProfile(
        karakas=karakas,
        karakamsha=karakamsha,
        ishta_kashta=ishta_kashta,
        karma_segments=segments,
        eclipse_alignments=eclipse_roles,
    )
