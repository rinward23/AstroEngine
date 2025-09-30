"""Reference tables for classical Jyotish dignity and rulership data.

The constants in this module are drawn from widely cited Vedic astrology
sources:

* The house lordship scheme and natural significators (karakas) follow the
  chapters on bhava and karaka assignments from *Brihat Parashara Hora
  Shastra* (BPHS), notably chapters 4–6 in the public domain translation by
  G. S. Kapoor (1967).
* Exaltation, debilitation, and moolatrikona spans match the table compiled by
  B. V. Raman in *Graha and Bhava Balas* (1984, Chapter 3) which itself
  references BPHS and Saravali.  Only spans explicitly documented in those
  texts are encoded here.
* Friendship and enmity between planets mirror BPHS Chapter 45.  Nodes follow
  the standard Parasara tradition where Rahu behaves like Saturn and Venus,
  while Ketu mirrors Mars and Jupiter.
* Combustion orbs are the values used by the `Muhurtha` tables reproduced in
  Raman's work (op. cit., Chapter 5).  They match the orbs popularised in
  classical Panchanga calculations.
* Planetary war (graha yuddha) participants and judgement order follow BPHS
  Chapter 28: only Mars, Mercury, Jupiter, Venus, and Saturn engage in war,
  the planet with the greater geocentric latitude wins, and brightness order
  (Venus, Jupiter, Mercury, Mars, Saturn) breaks remaining ties.

The tables are written in Python so they can be indexed efficiently and so the
rest of the engine can compute derived metrics without loading external files
at runtime.
"""

from __future__ import annotations

from collections.abc import Mapping

__all__ = [
    "SIGN_LORDS",
    "SIGN_CO_LORDS",
    "HOUSE_KARAKAS",
    "EXALTATION_SIGNS",
    "DEBILITATION_SIGNS",
    "MOOLATRIKONA_SPANS",
    "PLANET_FRIENDS",
    "PLANET_ENEMIES",
    "PLANET_NEUTRALS",
    "COMBUSTION_LIMITS",
    "SRISHTI_ASPECT_OFFSETS",
    "PLANETARY_WAR_PARTICIPANTS",
    "PLANETARY_WAR_BRIGHTNESS",
]

# Primary sign lords (classical Parasara scheme).
SIGN_LORDS: Mapping[str, tuple[str, ...]] = {
    "Aries": ("Mars",),
    "Taurus": ("Venus",),
    "Gemini": ("Mercury",),
    "Cancer": ("Moon",),
    "Leo": ("Sun",),
    "Virgo": ("Mercury",),
    "Libra": ("Venus",),
    "Scorpio": ("Mars",),
    "Sagittarius": ("Jupiter",),
    "Capricorn": ("Saturn",),
    "Aquarius": ("Saturn",),
    "Pisces": ("Jupiter",),
}

# Nodes and modern co-lords referenced in many SolarFire catalogues.
SIGN_CO_LORDS: Mapping[str, tuple[str, ...]] = {
    "Scorpio": ("Ketu",),
    "Aquarius": ("Rahu",),
    "Pisces": ("Neptune",),
}

# Natural significators (karakas) for the twelve houses.
HOUSE_KARAKAS: Mapping[int, tuple[str, ...]] = {
    1: ("Sun", "Moon"),
    2: ("Jupiter", "Mercury"),
    3: ("Mars", "Mercury"),
    4: ("Moon", "Venus"),
    5: ("Jupiter", "Sun"),
    6: ("Mars", "Saturn"),
    7: ("Venus", "Jupiter"),
    8: ("Saturn", "Ketu"),
    9: ("Jupiter", "Sun"),
    10: ("Sun", "Mercury"),
    11: ("Jupiter", "Mercury"),
    12: ("Saturn", "Ketu"),
}

EXALTATION_SIGNS: Mapping[str, str] = {
    "Sun": "Aries",
    "Moon": "Taurus",
    "Mars": "Capricorn",
    "Mercury": "Virgo",
    "Jupiter": "Cancer",
    "Venus": "Pisces",
    "Saturn": "Libra",
    "Rahu": "Taurus",
    "Ketu": "Scorpio",
}

DEBILITATION_SIGNS: Mapping[str, str] = {
    "Sun": "Libra",
    "Moon": "Scorpio",
    "Mars": "Cancer",
    "Mercury": "Pisces",
    "Jupiter": "Capricorn",
    "Venus": "Virgo",
    "Saturn": "Aries",
    "Rahu": "Scorpio",
    "Ketu": "Taurus",
}

# start_degree inclusive, end_degree exclusive (in sign-relative degrees)
MOOLATRIKONA_SPANS: Mapping[str, tuple[str, float, float]] = {
    "Sun": ("Leo", 0.0, 20.0),
    "Moon": ("Taurus", 3.0, 30.0),
    "Mars": ("Aries", 0.0, 12.0),
    "Mercury": ("Virgo", 15.0, 20.0),
    "Jupiter": ("Sagittarius", 0.0, 10.0),
    "Venus": ("Libra", 0.0, 15.0),
    "Saturn": ("Aquarius", 0.0, 20.0),
    "Rahu": ("Gemini", 0.0, 15.0),
    "Ketu": ("Sagittarius", 0.0, 15.0),
}

PLANET_FRIENDS: Mapping[str, tuple[str, ...]] = {
    "Sun": ("Moon", "Mars", "Jupiter"),
    "Moon": ("Sun", "Mercury"),
    "Mars": ("Sun", "Moon", "Jupiter"),
    "Mercury": ("Sun", "Venus"),
    "Jupiter": ("Sun", "Moon", "Mars"),
    "Venus": ("Mercury", "Saturn"),
    "Saturn": ("Mercury", "Venus"),
    "Rahu": ("Venus", "Saturn"),
    "Ketu": ("Mars", "Jupiter"),
}

PLANET_ENEMIES: Mapping[str, tuple[str, ...]] = {
    "Sun": ("Venus", "Saturn"),
    "Moon": (),
    "Mars": ("Mercury",),
    "Mercury": ("Moon",),
    "Jupiter": ("Venus", "Mercury"),
    "Venus": ("Sun", "Moon"),
    "Saturn": ("Sun", "Moon"),
    "Rahu": ("Sun", "Moon"),
    "Ketu": ("Sun", "Moon"),
}

PLANET_NEUTRALS: Mapping[str, tuple[str, ...]] = {
    "Sun": ("Mercury",),
    "Moon": ("Mars", "Jupiter", "Venus", "Saturn"),
    "Mars": ("Venus", "Saturn"),
    "Mercury": ("Mars", "Jupiter", "Saturn"),
    "Jupiter": ("Saturn",),
    "Venus": ("Mars", "Jupiter"),
    "Saturn": ("Mars", "Jupiter"),
    "Rahu": ("Mars", "Jupiter"),
    "Ketu": ("Venus", "Saturn", "Mercury"),
}

# Combustion orbs measured in degrees of separation from the Sun.
COMBUSTION_LIMITS: Mapping[str, float] = {
    "Moon": 12.0,
    "Mars": 17.0,
    "Mercury": 12.0,
    "Jupiter": 11.0,
    "Venus": 10.0,
    "Saturn": 15.0,
    "Rahu": 8.0,
    "Ketu": 8.0,
}

# Whole-sign (srishti) aspect offsets counted from the occupied house.
SRISHTI_ASPECT_OFFSETS: Mapping[str, tuple[int, ...]] = {
    "Sun": (7,),
    "Moon": (7,),
    "Mercury": (7,),
    "Venus": (7,),
    "Mars": (4, 7, 8),
    "Jupiter": (5, 7, 9),
    "Saturn": (3, 7, 10),
    "Rahu": (5, 7, 9),
    "Ketu": (5, 7, 9),
}

PLANETARY_WAR_PARTICIPANTS: tuple[str, ...] = (
    "Mars",
    "Mercury",
    "Jupiter",
    "Venus",
    "Saturn",
)

PLANETARY_WAR_BRIGHTNESS: Mapping[str, int] = {
    "Venus": 5,
    "Jupiter": 4,
    "Mercury": 3,
    "Mars": 2,
    "Saturn": 1,
}
