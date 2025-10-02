from __future__ import annotations

from astroengine.ephemeris import BodyPosition, HousePositions
from astroengine.jyotish import (
    determine_house_lords,
    detect_graha_yuddha,
    evaluate_house_claims,
    score_planet_strength,
)


def _make_body(
    name: str,
    longitude: float,
    *,
    latitude: float = 0.0,
    speed_longitude: float = 1.0,
) -> BodyPosition:
    return BodyPosition(
        body=name,
        julian_day=2451545.0,
        longitude=longitude,
        latitude=latitude,
        distance_au=1.0,
        speed_longitude=speed_longitude,
        speed_latitude=0.0,
        speed_distance=0.0,
        declination=0.0,
        speed_declination=0.0,
    )


def _aries_whole_sign_houses() -> HousePositions:
    cusps = tuple(float(i * 30.0) for i in range(12))
    return HousePositions(
        system="whole_sign",
        cusps=cusps,
        ascendant=0.0,
        midheaven=90.0,
    )


def _sample_positions() -> dict[str, BodyPosition]:
    return {
        "Sun": _make_body("Sun", 10.0),
        "Moon": _make_body("Moon", 35.0),  # Taurus
        "Mercury": _make_body("Mercury", 15.0),
        "Venus": _make_body("Venus", 355.0),  # Pisces
        "Mars": _make_body("Mars", 70.0),  # Gemini
        "Jupiter": _make_body("Jupiter", 100.0),  # Cancer
        "Saturn": _make_body("Saturn", 195.0, speed_longitude=-0.5),  # Libra retrograde
    }


def test_determine_house_lords_matches_parasara_tables() -> None:
    houses = _aries_whole_sign_houses()
    lords = determine_house_lords(houses)
    assert lords[1][0] == "Mars"
    assert lords[4][0] == "Moon"
    assert lords[7][0] == "Venus"
    assert lords[10][0] == "Saturn"


def test_strength_scoring_flags_dignity_combustion_and_retrograde() -> None:
    houses = _aries_whole_sign_houses()
    positions = _sample_positions()
    # Mercury is within 5° of the Sun and should be marked combust.
    mercury_strength = score_planet_strength(
        "Mercury",
        positions["Mercury"],
        houses=houses,
        sun_position=positions["Sun"],
        graha_roles={},
    )
    assert mercury_strength.is_combust
    assert mercury_strength.contributions["dignity"] < 1.0
    assert mercury_strength.contributions["combustion"] < 0.0

    jupiter_strength = score_planet_strength(
        "Jupiter",
        positions["Jupiter"],
        houses=houses,
        sun_position=positions["Sun"],
        graha_roles={},
    )
    assert jupiter_strength.dignity == "exaltation"
    assert jupiter_strength.total > mercury_strength.total

    saturn_strength = score_planet_strength(
        "Saturn",
        positions["Saturn"],
        houses=houses,
        sun_position=positions["Sun"],
        graha_roles={},
    )
    assert saturn_strength.is_retrograde
    assert "retrograde" in saturn_strength.contributions


def test_house_claims_promote_exalted_ruler_over_exalted_occupant() -> None:
    houses = _aries_whole_sign_houses()
    positions = _sample_positions()
    claims = evaluate_house_claims(positions, houses)

    first_house = claims[1]
    assert first_house.winner is not None
    assert first_house.winner.planet == "Sun"
    assert first_house.winner.strength.dignity == "exaltation"

    fourth_house = claims[4]
    assert fourth_house.winner is not None
    # Moon should win as ruler despite Jupiter's exaltation in the house.
    assert fourth_house.winner.planet == "Moon"
    occupant_planets = {claim.planet for claim in fourth_house.claims if claim.claim_type == "occupant"}
    assert "Jupiter" in occupant_planets


def test_detect_graha_yuddha_uses_latitude_priority() -> None:
    positions = {
        "Sun": _make_body("Sun", 0.0),
        "Mars": _make_body("Mars", 70.0, latitude=1.2),
        "Mercury": _make_body("Mercury", 70.5, latitude=0.3),
    }
    outcomes = detect_graha_yuddha(positions)
    assert outcomes, "Expected graha yuddha between Mars and Mercury"
    war = outcomes[0]
    assert {"Mars", "Mercury"} == set(war.planets)
    assert war.winner == "Mars"
    assert war.rationale == "higher_latitude"
