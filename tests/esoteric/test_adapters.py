from datetime import date

from astroengine.esoteric import numerology_mapper, tarot_mapper
from astroengine.utils.i18n import get_locale, set_locale


def test_tarot_mapper_provides_cards_and_disclaimer() -> None:
    result = tarot_mapper(planet="Sun", sign="Aries", house=1)
    assert "disclaimer" in result
    assert "Tarot" in result["disclaimer"] or "Tarot" in result["disclaimer"].title()
    planet_entry = result["planet"]
    assert planet_entry["card"] == "The Sun"
    assert "Sun" in planet_entry["prompt"]
    sign_entry = result["sign"]
    assert sign_entry["card"] == "The Emperor"
    assert "Aries" in sign_entry["prompt"]
    house_entry = result["house"]
    assert house_entry["card"]


def test_tarot_mapper_handles_unknown_house() -> None:
    result = tarot_mapper(house=15)
    assert result["house"]["card"] is None
    assert "House 15" in result["house"]["prompt"]


def test_numerology_mapper_calculations() -> None:
    dob = date(1990, 7, 16)
    payload = numerology_mapper(dob)
    assert payload["life_path"]["value"] == 33
    assert payload["life_path"]["is_master"] is True
    assert payload["birth_day"]["value"] == 7
    assert payload["attitude"]["value"] == 5


def test_adapters_translate_with_locale() -> None:
    original = get_locale()
    try:
        set_locale("es")
        tarot = tarot_mapper(planet="Moon", sign="Cancer", house=4)
        assert "tarot" in tarot["disclaimer"].lower()
        numerology = numerology_mapper(date(1985, 12, 3))
        assert "Camino" in numerology["life_path"]["label"]
    finally:
        set_locale(original)
