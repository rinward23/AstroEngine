from core.interpret_plus.engine import interpret


PACK = {
    "rulepack": "test-pack",
    "version": "1",
    "tag_map": {
        "chemistry": {"bucket": "chemistry", "weight": 1.0},
        "stability": {"bucket": "stability", "weight": 1.0},
        "spark": {"bucket": "chemistry", "weight": 1.1},
    },
    "profiles": {
        "default": {"tags": {}},
        "chemistry_plus": {"tags": {"chemistry": 1.2, "stability": 0.9}},
    },
    "rules": [
        {
            "id": "syn_sun_moon_harmony",
            "scope": "synastry",
            "when": {
                "bodiesA": ["Sun"],
                "bodiesB": ["Moon"],
                "family": ["harmonious"],
                "min_severity": 0.4,
            },
            "then": {
                "title": "Sun–Moon Harmony",
                "tags": ["chemistry", "stability"],
                "base_score": 0.8,
                "text": "{a} {aspect_symbol} {b}",
            },
        },
        {
            "id": "syn_group_saturn",
            "scope": "synastry",
            "when": {
                "group": {
                    "any": [
                        {"bodiesA": ["Saturn"], "bodiesB": ["*"], "aspects": [0, 90, 180], "min_severity": 0.3},
                        {"bodiesA": ["*"], "bodiesB": ["Saturn"], "aspects": [0, 90, 180], "min_severity": 0.3},
                    ],
                    "count_at_least": 2,
                }
            },
            "then": {
                "title": "Saturn Theme Strong",
                "tags": ["stability"],
                "base_score": 0.7,
                "boost": {"by": 1.1, "cap": 0.95},
                "text": "{count} Saturn links anchor the relationship",
                "limit": {"per_pair": True, "max": 1},
            },
        },
        {
            "id": "comp_venus_house7",
            "scope": "composite",
            "when": {
                "house": {
                    "scope": "composite",
                    "target": ["Venus"],
                    "in": ["VII"],
                }
            },
            "then": {
                "title": "Composite Venus in 7th",
                "tags": ["spark"],
                "base_score": 0.6,
                "text": "Composite Venus emphasises partnership duties",
            },
        },
    ],
}


def test_synastry_rule_and_profile_weights():
    hits = [
        {"a": "Sun", "b": "Moon", "aspect": "trine", "severity": 0.7},
        {"a": "Saturn", "b": "Venus", "aspect": "square", "severity": 0.6},
        {"a": "Saturn", "b": "Moon", "aspect": "opposition", "severity": 0.55},
    ]
    req = {"scope": "synastry", "hits": hits, "profile": "chemistry_plus"}
    out = interpret(req, PACK)
    assert [finding.id for finding in out] == ["syn_sun_moon_harmony", "syn_group_saturn"]
    assert out[0].score > out[1].score
    assert "Sun" in out[0].text


def test_composite_house_overlay():
    req = {
        "scope": "composite",
        "positions": {"Venus": 210.0},
        "houses": {"Venus": "VII"},
    }
    out = interpret(req, PACK)
    assert len(out) == 1
    assert out[0].id == "comp_venus_house7"
