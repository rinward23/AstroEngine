"""Catalog definitions for VCA Outline bodies and points."""

from __future__ import annotations

VCA_CORE_BODIES = [
    "sun",
    "moon",
    "mercury",
    "venus",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
    "pluto",
    "north_node",
    "south_node",
    "chiron",
]

VCA_EXT_ASTEROIDS = [
    "ceres",
    "pallas",
    "juno",
    "vesta",
    "hygiea",
    "eros",
    "psyche",
    "isis",
    "lilith1181",
    "sappho",
    "panacea",
    "astraea",
    "hekate",
    "fortuna",
    "nemesis",
]

VCA_CENTAURS = [
    "pholus",
    "nessus",
    "chariklo",
    "okyrhoe",
    "asbolus",
    "thereus",
    "hylonome",
    "cyllarus",
]

VCA_TNOS = [
    "eris",
    "haumea",
    "makemake",
    "sedna",
    "orcus",
    "quaoar",
    "varuna",
    "ixion",
    "gonggong",
]

VCA_SENSITIVE_POINTS = [
    "asc",
    "dsc",
    "mc",
    "ic",
    "vertex",
    "antivertex",
    "east_point",
    "polar_asc",
    "lot_fortune",
    "lot_spirit",
    "black_moon_lilith",
    "priapus",
    "prenatal_eclipse",
]


__all__ = [
    "VCA_CORE_BODIES",
    "VCA_EXT_ASTEROIDS",
    "VCA_CENTAURS",
    "VCA_TNOS",
    "VCA_SENSITIVE_POINTS",
]
