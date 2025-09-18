from astroengine.domains import DomainResolver, ZODIAC_ELEMENT_MAP


def test_elements_triplicity_mapping() -> None:
    assert ZODIAC_ELEMENT_MAP[0] == "FIRE"
    assert ZODIAC_ELEMENT_MAP[1] == "EARTH"
    assert ZODIAC_ELEMENT_MAP[2] == "AIR"
    assert ZODIAC_ELEMENT_MAP[3] == "WATER"
    assert ZODIAC_ELEMENT_MAP[10] == "AIR"
    assert ZODIAC_ELEMENT_MAP[11] == "WATER"


def test_domain_resolver_merges_and_normalizes() -> None:
    resolver = DomainResolver()
    result = resolver.resolve(sign_index=2, planet_key="mercury", house_index=3)
    assert result.elements == ["AIR"]
    assert result.domains
    top = max(result.domains, key=result.domains.get)
    assert top == "MIND"

