from astroengine.utils import i18n


def test_translate_defaults_to_english() -> None:
    i18n.set_locale("en")
    assert (
        i18n.translate("narrative.prompt.intro")
        == "You are an astrology interpreter summarizing key events for the reader."
    )


def test_translate_switches_locale() -> None:
    original = i18n.get_locale()
    try:
        i18n.set_locale("es")
        assert "astrológico" in i18n.translate("narrative.prompt.intro")
    finally:
        i18n.set_locale(original)


def test_translate_falls_back_to_key_for_unknown() -> None:
    assert i18n.translate("nonexistent.key") == "nonexistent.key"
