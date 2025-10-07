"""Resolve Hyleg and Alcocoden according to traditional heuristics."""

from __future__ import annotations

from collections.abc import Iterable

from ..traditional.dignities import bounds_ruler, sign_dignities
from ..traditional.models import AlcocodenResult, ChartCtx, HylegResult, LifeProfile
from ..traditional.profections import SIGN_RULERS

__all__ = ["find_hyleg", "find_alcocoden"]

SIGN_SEQUENCE = (
    "aries",
    "taurus",
    "gemini",
    "cancer",
    "leo",
    "virgo",
    "libra",
    "scorpio",
    "sagittarius",
    "capricorn",
    "aquarius",
    "pisces",
)


def _sign_from_degree(degree: float) -> str:
    index = int(degree % 360.0 // 30.0)
    return SIGN_SEQUENCE[index]


def _house_from_degree(asc_degree: float, degree: float) -> int:
    asc_index = int(asc_degree % 360.0 // 30.0)
    sign_index = int(degree % 360.0 // 30.0)
    return ((sign_index - asc_index) % 12) + 1


def _candidate_names(is_day: bool, include_fortune: bool) -> Iterable[str]:
    primary = "Sun" if is_day else "Moon"
    secondary = "Moon" if is_day else "Sun"
    names = [primary, secondary, "Asc"]
    if include_fortune:
        names.append("Fortune")
    return names


def _degree_for_candidate(chart: ChartCtx, candidate: str) -> float | None:
    if candidate == "Asc":
        return chart.natal.houses.ascendant
    if candidate == "Fortune":
        value = chart.lot("Fortune")
        return value if value is not None else None
    pos = chart.natal.positions.get(candidate)
    return pos.longitude if pos else None


def _planet_key(name: str) -> str:
    return name.strip().lower()


def _score_house(house: int, weights: dict[str, float]) -> tuple[float, str | None]:
    if house in {1, 4, 7, 10}:
        return weights.get("angular", 1.0), "angular"
    if house in {2, 5, 8, 11}:
        return weights.get("succedent", 0.5), "succedent"
    if house in {3, 6, 9, 12}:
        return weights.get("cadent", 0.25), "cadent"
    return 0.0, None


def _score_dignities(
    candidate: str,
    sign: str,
    degree: float,
    profile: LifeProfile,
    is_day: bool,
) -> tuple[float, list[tuple[str, float]]]:
    weights = dict(profile.dignity_weights)
    score = 0.0
    trace: list[tuple[str, float]] = []
    planet_key = _planet_key(candidate)
    bundle = sign_dignities(sign)
    domicile = SIGN_RULERS.get(sign)
    if domicile == planet_key:
        value = weights.get("rulership", 0.0)
        score += value
        trace.append(("rulership", value))
    if bundle.exaltation == planet_key:
        value = weights.get("exaltation", 0.0)
        score += value
        trace.append(("exaltation", value))
    triplicity = bundle.triplicity_for_sect("day" if is_day else "night")
    if triplicity == planet_key:
        value = weights.get("triplicity", 0.0)
        score += value
        trace.append(("triplicity", value))
    term_ruler = bundle.bounds_ruler(degree)
    if term_ruler == planet_key:
        value = weights.get("bounds", 0.0)
        score += value
        trace.append(("bounds", value))
    face = bundle.face_ruler(degree)
    if face == planet_key:
        value = weights.get("face", 0.0)
        score += value
        trace.append(("face", value))
    return score, trace


def find_hyleg(chart: ChartCtx, profile: LifeProfile) -> HylegResult:
    """Select the strongest Hyleg candidate using classical dignities."""

    asc_degree = chart.natal.houses.ascendant
    is_day = chart.sect.is_day
    best: HylegResult | None = None
    weights = dict(profile.dignity_weights)
    for candidate in _candidate_names(is_day, profile.include_fortune):
        degree = _degree_for_candidate(chart, candidate)
        if degree is None:
            continue
        sign = _sign_from_degree(degree)
        house = _house_from_degree(asc_degree, degree)
        if house not in profile.house_candidates and candidate != "Asc":
            continue
        base_score, house_tag = _score_house(house, weights)
        trace: list[tuple[str, float]] = []
        notes: list[str] = [f"candidate={candidate}", f"sign={sign}", f"house={house}"]
        if house_tag:
            trace.append((house_tag, base_score))
        score = base_score
        if candidate in {"Sun", "Moon"}:
            dignity_score, dignity_trace = _score_dignities(
                candidate,
                sign,
                degree % 30.0,
                profile,
                is_day,
            )
            score += dignity_score
            trace.extend(dignity_trace)
            if candidate == chart.sect.luminary_of_sect:
                value = weights.get("sect", 0.0)
                score += value
                trace.append(("sect", value))
        elif candidate == "Asc":
            score += weights.get("angular", 1.0)
            trace.append(("ascendant", weights.get("angular", 1.0)))
        if candidate == "Fortune":
            notes.append("lot_of_fortune")
        result = HylegResult(
            body=candidate,
            degree=degree % 360.0,
            sign=sign,
            house=house,
            score=score,
            notes=tuple(notes),
            trace=tuple(trace),
        )
        if best is None or result.score > best.score:
            best = result
    if best is None:
        raise ValueError("No suitable Hyleg candidate found")
    return best


def find_alcocoden(chart: ChartCtx, hyleg: HylegResult, profile: LifeProfile) -> AlcocodenResult:
    """Return the Alcocoden (giver of years) for the supplied Hyleg."""

    degree = hyleg.degree % 360.0
    sign = hyleg.sign
    is_day = chart.sect.is_day
    term_ruler = bounds_ruler(sign, degree % 30.0)
    method = "bounds"
    confidence = 0.85 if term_ruler else 0.6
    trace: list[str] = []
    if term_ruler:
        trace.append(f"bounds:{term_ruler}")
        candidate = term_ruler
    else:
        bundle = sign_dignities(sign)
        scores: dict[str, float] = {}
        weights = dict(profile.dignity_weights)
        domicile = SIGN_RULERS.get(sign)
        if domicile:
            scores[domicile] = scores.get(domicile, 0.0) + weights.get("rulership", 0.0)
            trace.append(f"rulership:{domicile}")
        if bundle.exaltation:
            scores[bundle.exaltation] = scores.get(bundle.exaltation, 0.0) + weights.get(
                "exaltation", 0.0
            )
            trace.append(f"exaltation:{bundle.exaltation}")
        triplicity = bundle.triplicity_for_sect("day" if is_day else "night")
        if triplicity:
            scores[triplicity] = scores.get(triplicity, 0.0) + weights.get("triplicity", 0.0)
            trace.append(f"triplicity:{triplicity}")
        if bundle.bounds:
            for span in bundle.bounds:
                scores[span.ruler] = scores.get(span.ruler, 0.0) + weights.get("bounds", 0.0)
        if bundle.decans:
            for span in bundle.decans:
                scores[span.ruler] = scores.get(span.ruler, 0.0) + weights.get("face", 0.0)
        if not scores:
            raise ValueError("Unable to determine Alcocoden ruler")
        candidate = max(scores, key=scores.get)
        method = "dignities"
        confidence = 0.55
    years = profile.lifespan_years.get(candidate, None)
    notes = [f"method={method}", f"sign={sign}"]
    if profile.bounds_scheme:
        notes.append(f"bounds_scheme={profile.bounds_scheme}")
    return AlcocodenResult(
        body=candidate.title(),
        method=method,
        indicative_years=years,
        confidence=confidence,
        notes=tuple(notes),
        trace=tuple(trace),
    )
