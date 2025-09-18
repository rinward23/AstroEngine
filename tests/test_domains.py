from __future__ import annotations

import pytest

# >>> AUTO-GEN BEGIN: Tests Domains v1.0
from astroengine.domains import ZODIAC_ELEMENT_MAP, DomainResolver


def test_elements_triplicity_mapping():
    # Aries..Pisces
    assert ZODIAC_ELEMENT_MAP[0] == "FIRE"
    assert ZODIAC_ELEMENT_MAP[1] == "EARTH"
    assert ZODIAC_ELEMENT_MAP[2] == "AIR"
    assert ZODIAC_ELEMENT_MAP[3] == "WATER"
    assert ZODIAC_ELEMENT_MAP[10] == "AIR"   # Aquarius
    assert ZODIAC_ELEMENT_MAP[11] == "WATER" # Pisces


def test_domain_resolver_merges_and_normalizes():
    r = DomainResolver()
    # Mercury in Gemini 3rd house → MIND should dominate; elements FIRE/EARTH/AIR/WATER: AIR
    res = r.resolve(sign_index=2, planet_key="mercury", house_index=3)
    assert res.elements == ["AIR"]
    assert res.domains
    # top domain is MIND
    top = max(res.domains, key=res.domains.get)
    assert top == "MIND"
# >>> AUTO-GEN END: Tests Domains v1.0


def test_domain_resolver_respects_overrides():
    resolver = DomainResolver()
    overrides = {"planet_weights": {"mercury": {"SPIRIT": 5.0}}}
    res = resolver.resolve(sign_index=2, planet_key="mercury", house_index=3, overrides=overrides)
    assert res.domains.get("SPIRIT") == 1.0


def test_domain_resolver_invalid_sign_raises():
    resolver = DomainResolver()
    with pytest.raises(ValueError):
        resolver.resolve(sign_index=12, planet_key="sun")
