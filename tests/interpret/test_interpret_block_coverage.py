from astroengine.interpret import (
    HOUSES,
    LUMINARY_ASPECTS,
    MAJOR_BODIES,
    ZODIAC_SIGNS,
    build_interpretation_blocks,
    house_block,
    luminary_aspect_block,
    sign_block,
)
from astroengine.utils.i18n import get_locale, set_locale, translate


def test_sign_blocks_cover_all_major_bodies() -> None:
    fallback_fragment = translate("interpretation.no_content", subject="dummy").split(" ")[0]
    for body in MAJOR_BODIES:
        for sign in ZODIAC_SIGNS:
            text = sign_block(body, sign)
            assert text
            assert fallback_fragment not in text


def test_house_blocks_cover_all_major_bodies() -> None:
    fallback = translate("interpretation.no_content", subject="x")
    for body in MAJOR_BODIES:
        for house in HOUSES:
            text = house_block(body, house)
            assert text
            assert text != fallback


def test_luminary_aspect_blocks_cover_all_major_bodies() -> None:
    for body in MAJOR_BODIES:
        for luminary in ("Sun", "Moon"):
            for aspect in LUMINARY_ASPECTS:
                text = luminary_aspect_block(body, luminary, aspect)
                assert text
                assert "No curated interpretation" not in text


def test_invalid_inputs_return_fallback() -> None:
    expected = translate(
        "interpretation.no_content",
        subject="Ceres in Perseus",
    )
    assert (
        sign_block("Ceres", "Perseus")
        == expected
    )
    assert (
        house_block("Ceres", 99)
        == translate("interpretation.no_content", subject="Ceres in house 99")
    )
    assert (
        luminary_aspect_block("Ceres", "Sun", 13)
        == translate("interpretation.no_content", subject="Ceres 13 Sun")
    )


def test_build_interpretation_blocks_payload_dimensions() -> None:
    payload = build_interpretation_blocks()
    assert len(payload["signs"]) == len(MAJOR_BODIES) * len(ZODIAC_SIGNS)
    assert len(payload["houses"]) == len(MAJOR_BODIES) * len(HOUSES)
    assert (
        len(payload["luminary_aspects"])
        == len(MAJOR_BODIES) * len(LUMINARY_ASPECTS) * 2
    )


def test_locale_switch_affects_blocks() -> None:
    original = get_locale()
    try:
        set_locale("es")
        text = sign_block("Sun", "Aries")
        assert "canaliza" in text
    finally:
        set_locale(original)
