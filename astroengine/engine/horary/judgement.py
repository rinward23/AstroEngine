from __future__ import annotations

from collections.abc import Iterable

"""Judgement engine tallying horary testimonies."""

from ...chart.natal import NatalChart
from .aspects_logic import aspect_between, find_collection, find_prohibition, find_translation
from .models import JudgementContribution, JudgementResult, RadicalityCheck, SignificatorSet
from .profiles import HoraryProfile

__all__ = ["score_testimonies"]


_BENEFICS = {"Venus", "Jupiter"}
_MALEFICS = {"Mars", "Saturn"}
_ANGULAR_HOUSES = {1, 4, 7, 10}


def _house_for_longitude(chart: NatalChart, longitude: float) -> int:
    cusps = [c % 360.0 for c in chart.houses.cusps[:12]]
    lon = longitude % 360.0
    for idx in range(12):
        start = cusps[idx]
        end = cusps[(idx + 1) % 12]
        if start <= end:
            if start <= lon < end:
                return idx + 1
        else:
            if lon >= start or lon < end:
                return idx + 1
    return 12


def _lookup_weight(weights: dict[str, float], key: str) -> float:
    return float(weights.get(key, 0.0))


def _add(
    contributions: list[JudgementContribution],
    code: str,
    label: str,
    weight: float,
    value: float,
    rationale: str,
) -> float:
    score = weight * value
    contributions.append(
        JudgementContribution(
            code=code,
            label=label,
            weight=weight,
            value=value,
            score=score,
            rationale=rationale,
        )
    )
    return score


def _moon_next_aspect(
    chart: NatalChart,
    profile: HoraryProfile,
    *,
    exclude: Iterable[str] = (),
) -> tuple[str, float] | None:
    best_body: str | None = None
    best_time: float | None = None
    for name in chart.positions:
        if name == "Moon" or name in exclude:
            continue
        contact = aspect_between(chart, "Moon", name, profile)
        if contact is None or not contact.applying or contact.perfection_time is None:
            continue
        delta_days = (contact.perfection_time - chart.moment).total_seconds() / 86400.0
        if delta_days < 0:
            continue
        if best_time is None or delta_days < best_time:
            best_time = delta_days
            best_body = name
    if best_body is None or best_time is None:
        return None
    return best_body, best_time


def score_testimonies(
    chart: NatalChart,
    significators: SignificatorSet,
    checks: Iterable[RadicalityCheck],
    profile: HoraryProfile,
) -> JudgementResult:
    """Aggregate horary testimonies into a final score and classification."""

    weights = dict(profile.testimony_policy().entries)
    contributions: list[JudgementContribution] = []
    total = 0.0

    main_contact = aspect_between(
        chart, significators.querent.body, significators.quesited.body, profile
    )
    if main_contact is not None and main_contact.applying:
        mutual = (
            significators.quesited.body in significators.querent.receptions
            and significators.querent.body in significators.quesited.receptions
        )
        any_reception = (
            significators.quesited.body in significators.querent.receptions
            or significators.querent.body in significators.quesited.receptions
        )
        if mutual or any_reception:
            weight = _lookup_weight(weights, "applying_with_reception")
            if weight:
                total += _add(
                    contributions,
                    "applying_with_reception",
                    "Applying aspect with reception",
                    weight,
                    1.0,
                    f"{significators.querent.body} applies to {significators.quesited.body} with reception",
                )
        else:
            weight = _lookup_weight(weights, "applying_no_reception")
            if weight:
                total += _add(
                    contributions,
                    "applying_no_reception",
                    "Applying aspect without reception",
                    weight,
                    1.0,
                    f"{significators.querent.body} applies to {significators.quesited.body}",
                )
    elif main_contact is not None and not main_contact.applying:
        weight = _lookup_weight(weights, "applying_no_reception")
        if weight:
            total += _add(
                contributions,
                "applying_no_reception",
                "Separating aspect",
                weight,
                -1.0,
                "Primary significators are separating",
            )

    translation = find_translation(
        chart, significators.querent.body, significators.quesited.body, profile
    )
    if translation is not None:
        weight = _lookup_weight(weights, "translation")
        if weight:
            total += _add(
                contributions,
                "translation",
                "Translation of light",
                weight,
                1.0,
                f"{translation.translator} translates light between the significators",
            )

    collection = find_collection(
        chart, significators.querent.body, significators.quesited.body, profile
    )
    if collection is not None:
        weight = _lookup_weight(weights, "collection")
        if weight:
            total += _add(
                contributions,
                "collection",
                "Collection of light",
                weight,
                1.0,
                f"{collection.collector} collects light from both significators",
            )

    prohibition = find_prohibition(
        chart, significators.querent.body, significators.quesited.body, profile
    )
    if prohibition is not None:
        weight = _lookup_weight(weights, "prohibition")
        if weight:
            total += _add(
                contributions,
                "prohibition",
                "Prohibition",
                weight,
                1.0,
                f"{prohibition.preventing_body} perfects with a significator before the main aspect",
            )

    next_contact = _moon_next_aspect(chart, profile, exclude={significators.querent.body, significators.quesited.body})
    if next_contact is not None:
        target, days = next_contact
        weight = _lookup_weight(weights, "moon_next_good")
        if weight:
            if target in _BENEFICS:
                value = 1.0
                rationale = f"Moon next applies to benefic {target}"
            elif target in _MALEFICS:
                value = -1.0
                rationale = f"Moon next applies to malefic {target}"
            else:
                value = 0.0
                rationale = f"Moon next applies to {target}"
            total += _add(
                contributions,
                "moon_next_good",
                "Moon's next aspect",
                weight,
                value,
                rationale,
            )

    malefic_hits: list[str] = []
    for name in _MALEFICS:
        pos = chart.positions.get(name)
        if pos is None:
            continue
        house = _house_for_longitude(chart, pos.longitude)
        if house in _ANGULAR_HOUSES:
            malefic_hits.append(name)
    if malefic_hits:
        weight = _lookup_weight(weights, "malefic_on_angle")
        if weight:
            total += _add(
                contributions,
                "malefic_on_angle",
                "Malefic on angle",
                weight,
                1.0,
                f"Angular malefics: {', '.join(malefic_hits)}",
            )

    # Essential dignity scores
    total += _add(
        contributions,
        "querent_dignity",
        "Querent dignity",
        1.0,
        significators.querent.dignities.score or 0.0,
        "Querent ruler essential dignity score",
    )
    total += _add(
        contributions,
        "quesited_dignity",
        "Quesited dignity",
        1.0,
        significators.quesited.dignities.score or 0.0,
        "Quesited ruler essential dignity score",
    )

    for check in checks:
        if check.caution_weight:
            total += _add(
                contributions,
                f"radicality_{check.code}",
                f"Radicality: {check.code}",
                1.0,
                check.caution_weight,
                check.reason,
            )

    thresholds = profile.thresholds()
    if total >= thresholds.yes:
        classification = "Yes"
    elif total >= thresholds.qualified:
        classification = "Qualified"
    elif total >= thresholds.weak:
        classification = "Weak"
    else:
        classification = "No"

    contributions.sort(key=lambda item: item.score, reverse=True)
    return JudgementResult(
        score=total,
        classification=classification,
        contributions=tuple(contributions),
    )

