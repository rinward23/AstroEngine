from astroengine.domains import ZODIAC_ELEMENT_MAP, DomainResolver


def test_elements_triplicity_mapping():
    assert ZODIAC_ELEMENT_MAP[0] == "FIRE"
    assert ZODIAC_ELEMENT_MAP[1] == "EARTH"
    assert ZODIAC_ELEMENT_MAP[2] == "AIR"
    assert ZODIAC_ELEMENT_MAP[3] == "WATER"
    assert ZODIAC_ELEMENT_MAP[10] == "AIR"
    assert ZODIAC_ELEMENT_MAP[11] == "WATER"


def test_domain_resolver_merges_and_normalizes():
    resolver = DomainResolver()
    resolution = resolver.resolve(sign_index=2, planet_key="mercury", house_index=3)
    assert resolution.elements == ["AIR"]
    assert resolution.domains
    top = max(resolution.domains, key=resolution.domains.get)
    assert top == "MIND"
