from core.interpret_plus.engine import interpret


HITS = [
    {"a": "Sun", "b": "Moon", "aspect": "trine", "severity": 0.6},
    {"a": "Venus", "b": "Mars", "aspect": "conjunction", "severity": 0.5},
    {"a": "Saturn", "b": "Venus", "aspect": "square", "severity": 0.4},
]


RULES = [
    {
        "id": "syn_sun_moon_harmony",
        "scope": "synastry",
        "when": {
            "bodies": ["Sun", "Moon"],
            "aspect_in": ["trine", "sextile"],
            "min_severity": 0.3,
        },
        "score": 1.2,
        "text": "{a} {aspect} {b}",
    },
    {
        "id": "syn_venus_mars_chem",
        "scope": "synastry",
        "when": {
            "bodies": ["Venus", "Mars"],
            "aspect_in": ["conjunction"],
            "min_severity": 0.2,
        },
        "score": 1.4,
        "text": "{a}-{b} {aspect} wow",
    },
    {
        "id": "syn_saturn_hard",
        "scope": "synastry",
        "when": {
            "bodies": ["Saturn"],
            "aspect_in": ["conjunction", "square", "opposition"],
            "min_severity": 0.2,
        },
        "score": 1.6,
        "text": "Saturn binding",
    },
]


def test_synastry_findings_sorted_and_formatted():
    req = {"scope": "synastry", "hits": HITS}
    out = interpret(req, RULES)
    assert len(out) == 3
    assert out[0].id in {"syn_venus_mars_chem", "syn_sun_moon_harmony", "syn_saturn_hard"}
    assert any(token in out[1].text for token in {"trine", "wow", "Saturn"})


def test_composite_longitude_rule():
    rules = [
        {
            "id": "comp_venus_early",
            "scope": "composite",
            "when": {"bodies": ["Venus"], "longitude_ranges": [[0, 30]]},
            "score": 0.8,
            "text": "Composite {body} ok",
        }
    ]
    req = {"scope": "composite", "positions": {"Venus": 5.0}}
    out = interpret(req, rules)
    assert len(out) == 1
    assert out[0].text.startswith("Composite Venus")


def test_davison_longitude_rule():
    rules = [
        {
            "id": "dav_sun_early",
            "scope": "davison",
            "when": {"bodies": ["Sun"], "longitude_ranges": [[0, 15]]},
            "score": 0.7,
            "text": "Davison {body} early",
        }
    ]
    req = {"scope": "davison", "positions": {"Sun": 10.0}}
    out = interpret(req, rules)
    assert len(out) == 1
    assert out[0].id == "dav_sun_early"
