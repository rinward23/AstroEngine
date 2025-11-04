"""Gochara (transit) analytics spanning natal, dasha, and divisional data.

This module processes time-stamped transit snapshots sourced from the
Swiss ephemeris adapters and compares them against natal placements,
active Vimśottarī (or other graha) dasha rulers, and divisional-chart
lords.  The analysis produces weighted interactions, retrograde triggers,
and alert payloads suitable for the predictive module registry.

All computations reference the supplied runtime datasets; no synthetic
positions or interpolated dashas are generated here.  The entry-point
:func:`analyse_gochar_transits` accepts the actual transit stream along
with natal and dasha context and returns a structured report while
delegating persistence and presentation to downstream modules.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime

from ...detectors.common import delta_deg
from ...timelords.profections import SIGN_RULERS
from .dasha_vimshottari import DashaPeriod

__all__ = [
    "TransitSnapshot",
    "TransitInteraction",
    "TransitAlert",
    "RetrogradeTrigger",
    "TransitWeightPolicy",
    "GocharTransitReport",
    "analyse_gochar_transits",
]


_ASPECT_DEGREES: Mapping[str, float] = {
    "conjunction": 0.0,
    "sextile": 60.0,
    "square": 90.0,
    "trine": 120.0,
    "opposition": 180.0,
}


def _default_aspect_orbs() -> dict[str, float]:
    return {
        "conjunction": 6.0,
        "sextile": 4.0,
        "square": 5.0,
        "trine": 5.0,
        "opposition": 6.0,
    }


def _default_aspect_weights() -> dict[str, float]:
    return {
        "conjunction": 1.0,
        "sextile": 0.6,
        "square": 0.75,
        "trine": 0.85,
        "opposition": 0.9,
    }


OUTER_PLANETS = {"jupiter", "saturn", "uranus", "neptune", "pluto"}


@dataclass(frozen=True)
class TransitSnapshot:
    """Container describing a single moment of transit positions."""

    timestamp: datetime
    positions: Mapping[str, Mapping[str, object] | object]


@dataclass(frozen=True)
class TransitInteraction:
    """Weighted interaction between a transit body and a target."""

    timestamp: datetime
    moving: str
    target: str
    relation: str
    aspect: str
    orb: float
    score: float
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class TransitAlert:
    """Alert emitted when an interaction exceeds the configured threshold."""

    timestamp: datetime
    message: str
    score: float
    interaction: TransitInteraction
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrogradeTrigger:
    """Transition point where an outer planet flips motion direction."""

    timestamp: datetime
    body: str
    phase: str
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class TransitWeightPolicy:
    """Configuration for scoring and alerting gochara contacts."""

    aspect_orbs: Mapping[str, float] = field(default_factory=_default_aspect_orbs)
    aspect_weights: Mapping[str, float] = field(default_factory=_default_aspect_weights)
    dasha_bonus: float = 0.35
    divisional_bonus: float = 0.25
    moving_dasha_bonus: float = 0.15
    transit_contact_weight: float = 0.7
    retrograde_trigger_bonus: float = 0.5
    alert_threshold: float = 1.25


@dataclass(frozen=True)
class GocharTransitReport:
    """Aggregate payload returned by :func:`analyse_gochar_transits`."""

    interactions: tuple[TransitInteraction, ...]
    retrograde_triggers: tuple[RetrogradeTrigger, ...]
    alerts: tuple[TransitAlert, ...]


def _longitude_of(position: Mapping[str, object] | object) -> float | None:
    if isinstance(position, Mapping):
        for key in ("longitude", "lon", "lambda", "lambda_deg"):
            value = position.get(key)
            if value is not None:
                return float(value)
        return None
    return getattr(position, "longitude", None)


def _retrograde_flag(data: Mapping[str, object] | object) -> bool | None:
    if isinstance(data, Mapping):
        if "retrograde" in data:
            return bool(data["retrograde"])
        if "speed" in data:
            try:
                return float(data["speed"]) < 0.0
            except (TypeError, ValueError):
                return None
        if "motion" in data:
            try:
                return float(data["motion"]) < 0.0
            except (TypeError, ValueError):
                return None
        return None
    speed = getattr(data, "speed", None)
    if speed is not None:
        try:
            return float(speed) < 0.0
        except (TypeError, ValueError):
            return None
    retrograde = getattr(data, "retrograde", None)
    if retrograde is not None:
        return bool(retrograde)
    return None


def _active_dasha_index(
    periods: Sequence[DashaPeriod] | None,
    moment: datetime,
) -> dict[str, tuple[str, ...]]:
    index: dict[str, set[str]] = {}
    if not periods:
        return {}
    for period in periods:
        if period.start <= moment < period.end:
            ruler = period.ruler.lower()
            levels = index.setdefault(ruler, set())
            levels.add(period.level)
    return {ruler: tuple(sorted(levels)) for ruler, levels in index.items()}


def _index_divisional_lords(
    divisional_positions: Mapping[str, Mapping[str, Mapping[str, object] | object]] | None,
) -> dict[str, tuple[str, ...]]:
    index: dict[str, set[str]] = {}
    if not divisional_positions:
        return {}
    for chart_name, placements in divisional_positions.items():
        for _, payload in placements.items():
            if not isinstance(payload, Mapping):
                continue
            sign = payload.get("sign")
            if not isinstance(sign, str):
                continue
            ruler = SIGN_RULERS.get(sign.lower())
            if not ruler:
                continue
            entries = index.setdefault(ruler.lower(), set())
            entries.add(chart_name)
    return {ruler: tuple(sorted(charts)) for ruler, charts in index.items()}


def _resolve_aspect(
    moving_lon: float,
    target_lon: float,
    policy: TransitWeightPolicy,
) -> tuple[str, float, float, float] | None:
    delta = abs(delta_deg(moving_lon, target_lon))
    best: tuple[str, float, float, float] | None = None
    for name, angle in _ASPECT_DEGREES.items():
        orb_allow = float(policy.aspect_orbs.get(name, 0.0))
        if orb_allow <= 0.0:
            continue
        diff = abs(delta - angle)
        if diff > orb_allow:
            continue
        base_weight = float(policy.aspect_weights.get(name, 0.0))
        if base_weight <= 0.0:
            continue
        candidate = (name, diff, orb_allow, base_weight)
        if best is None or diff < best[1]:
            best = candidate
    return best


def _score_contact(
    base_weight: float,
    diff: float,
    orb_allow: float,
    *,
    multipliers: Iterable[float] = (),
) -> float:
    if orb_allow <= 0.0:
        return 0.0
    closeness = max(0.0, 1.0 - (diff / orb_allow))
    score = base_weight * closeness
    for multiplier in multipliers:
        score *= multiplier
    return score


def _detect_retrograde_triggers(
    snapshots: Sequence[TransitSnapshot],
) -> tuple[RetrogradeTrigger, ...]:
    if len(snapshots) < 2:
        return tuple()
    previous_flags: dict[str, bool] = {}
    triggers: list[RetrogradeTrigger] = []
    for snapshot in snapshots:
        for body, payload in snapshot.positions.items():
            retrograde = _retrograde_flag(payload)
            if retrograde is None:
                continue
            key = body.lower()
            prior = previous_flags.get(key)
            if prior is None:
                previous_flags[key] = retrograde
                continue
            if retrograde != prior and key in OUTER_PLANETS:
                phase = "retrograde" if retrograde else "direct"
                metadata = {"previous": "retrograde" if prior else "direct"}
                triggers.append(
                    RetrogradeTrigger(
                        timestamp=snapshot.timestamp,
                        body=body,
                        phase=phase,
                        metadata=metadata,
                    )
                )
            previous_flags[key] = retrograde
    return tuple(triggers)


def _build_trigger_index(triggers: Sequence[RetrogradeTrigger]) -> dict[datetime, set[str]]:
    index: dict[datetime, set[str]] = {}
    for trigger in triggers:
        bodies = index.setdefault(trigger.timestamp, set())
        bodies.add(trigger.body.lower())
    return index


def _evaluate_snapshot(
    snapshot: TransitSnapshot,
    natal_positions: Mapping[str, Mapping[str, object] | object],
    active_dasha: Mapping[str, tuple[str, ...]],
    divisional_index: Mapping[str, tuple[str, ...]],
    policy: TransitWeightPolicy,
    retrograde_bodies: Iterable[str],
) -> list[TransitInteraction]:
    retrograde_set = {body.lower() for body in retrograde_bodies}
    interactions: list[TransitInteraction] = []

    moving_items = list(snapshot.positions.items())
    natal_longitudes: dict[str, float] = {}
    for target, position in natal_positions.items():
        lon = _longitude_of(position)
        if lon is not None:
            natal_longitudes[target] = float(lon)

    divisional_targets = {
        ruler: divisional_index[ruler]
        for ruler in divisional_index
        if ruler in {name.lower() for name in natal_longitudes}
    }

    for moving_name, payload in moving_items:
        moving_lon = _longitude_of(payload)
        if moving_lon is None:
            continue
        moving_lower = moving_name.lower()
        moving_tags: list[str] = []
        moving_multiplier = 1.0
        moving_dasha_levels = active_dasha.get(moving_lower)
        if moving_dasha_levels:
            moving_multiplier *= 1.0 + policy.moving_dasha_bonus
            moving_tags.append("moving_dasha")
        if moving_lower in retrograde_set:
            moving_multiplier *= 1.0 + policy.retrograde_trigger_bonus
            moving_tags.append("retrograde_trigger")

        for target_name, target_lon in natal_longitudes.items():
            aspect_data = _resolve_aspect(moving_lon, target_lon, policy)
            if aspect_data is None:
                continue
            aspect_name, diff, orb_allow, base_weight = aspect_data
            target_lower = target_name.lower()
            multipliers: list[float] = [moving_multiplier]
            metadata: dict[str, object] = {
                "moving_longitude": moving_lon,
                "target_longitude": target_lon,
                "aspect_angle": _ASPECT_DEGREES[aspect_name],
                "orb_allow": orb_allow,
            }
            tags = list(moving_tags)

            dasha_levels = active_dasha.get(target_lower)
            if dasha_levels:
                multipliers.append(1.0 + policy.dasha_bonus)
                metadata["dasha_levels"] = dasha_levels
                tags.append("dasha")

            charts = divisional_targets.get(target_lower)
            if charts:
                multipliers.append(1.0 + policy.divisional_bonus)
                metadata["divisional_charts"] = charts
                tags.append("divisional_lord")

            score = _score_contact(
                base_weight,
                diff,
                orb_allow,
                multipliers=multipliers,
            )
            if score <= 0.0:
                continue

            metadata["orb"] = diff
            if tags:
                metadata["tags"] = tuple(sorted(set(tags)))
            if moving_dasha_levels:
                metadata["moving_dasha_levels"] = moving_dasha_levels

            interactions.append(
                TransitInteraction(
                    timestamp=snapshot.timestamp,
                    moving=moving_name,
                    target=target_name,
                    relation="natal",
                    aspect=aspect_name,
                    orb=diff,
                    score=score,
                    metadata=metadata,
                )
            )

    # Transit-to-transit aspects
    body_names = [name for name, payload in moving_items if _longitude_of(payload) is not None]
    for idx, moving_name in enumerate(body_names):
        moving_payload = snapshot.positions[moving_name]
        moving_lon = _longitude_of(moving_payload)
        if moving_lon is None:
            continue
        moving_lower = moving_name.lower()
        moving_multiplier = 1.0
        if moving_lower in retrograde_set:
            moving_multiplier *= 1.0 + policy.retrograde_trigger_bonus
        if moving_lower in active_dasha:
            moving_multiplier *= 1.0 + policy.moving_dasha_bonus

        for target_name in body_names[idx + 1 :]:
            target_payload = snapshot.positions[target_name]
            target_lon = _longitude_of(target_payload)
            if target_lon is None:
                continue
            aspect_data = _resolve_aspect(moving_lon, target_lon, policy)
            if aspect_data is None:
                continue
            aspect_name, diff, orb_allow, base_weight = aspect_data
            multipliers = [policy.transit_contact_weight, moving_multiplier]
            target_lower = target_name.lower()
            if target_lower in retrograde_set:
                multipliers.append(1.0 + policy.retrograde_trigger_bonus)
            if target_lower in active_dasha:
                multipliers.append(1.0 + policy.moving_dasha_bonus)

            score = _score_contact(base_weight, diff, orb_allow, multipliers=multipliers)
            if score <= 0.0:
                continue

            metadata = {
                "moving_longitude": moving_lon,
                "target_longitude": target_lon,
                "aspect_angle": _ASPECT_DEGREES[aspect_name],
                "orb_allow": orb_allow,
                "orb": diff,
                "relation": "transit_to_transit",
            }
            if moving_lower in active_dasha:
                metadata["moving_dasha_levels"] = active_dasha[moving_lower]
            if target_lower in active_dasha:
                metadata["target_dasha_levels"] = active_dasha[target_lower]

            interactions.append(
                TransitInteraction(
                    timestamp=snapshot.timestamp,
                    moving=moving_name,
                    target=target_name,
                    relation="transit",
                    aspect=aspect_name,
                    orb=diff,
                    score=score,
                    metadata=metadata,
                )
            )

    return interactions


def analyse_gochar_transits(
    snapshots: Sequence[TransitSnapshot],
    *,
    natal_positions: Mapping[str, Mapping[str, object] | object],
    dasha_periods: Sequence[DashaPeriod] | None = None,
    divisional_positions: Mapping[str, Mapping[str, Mapping[str, object] | object]] | None = None,
    policy: TransitWeightPolicy | None = None,
) -> GocharTransitReport:
    """Return transit analytics for ``snapshots`` against the provided context."""

    if not snapshots:
        return GocharTransitReport((), (), ())

    policy = policy or TransitWeightPolicy()
    ordered = tuple(sorted(snapshots, key=lambda snap: snap.timestamp))
    divisional_index = _index_divisional_lords(divisional_positions)
    retrograde_triggers = _detect_retrograde_triggers(ordered)
    trigger_index = _build_trigger_index(retrograde_triggers)

    interactions: list[TransitInteraction] = []
    alerts: list[TransitAlert] = []

    for snapshot in ordered:
        active_dasha = _active_dasha_index(dasha_periods, snapshot.timestamp)
        retrograde_bodies = trigger_index.get(snapshot.timestamp, set())
        snapshot_interactions = _evaluate_snapshot(
            snapshot,
            natal_positions,
            active_dasha,
            divisional_index,
            policy,
            retrograde_bodies,
        )
        interactions.extend(snapshot_interactions)
        for interaction in snapshot_interactions:
            if interaction.score >= policy.alert_threshold:
                message = (
                    f"{interaction.moving} {interaction.aspect} {interaction.target}"
                    f" (score {interaction.score:.2f})"
                )
                alert_metadata = {
                    "relation": interaction.relation,
                    **interaction.metadata,
                }
                alerts.append(
                    TransitAlert(
                        timestamp=interaction.timestamp,
                        message=message,
                        score=interaction.score,
                        interaction=interaction,
                        metadata=alert_metadata,
                    )
                )

    return GocharTransitReport(
        interactions=tuple(interactions),
        retrograde_triggers=retrograde_triggers,
        alerts=tuple(alerts),
    )
