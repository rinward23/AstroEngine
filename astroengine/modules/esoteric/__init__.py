"""Registry wiring for esoteric overlays (decans, tarot correspondences)."""

from __future__ import annotations

from ...esoteric import (
    ALCHEMY_STAGES,
    DECANS,
    ELDER_FUTHARK_RUNES,
    GEOMANTIC_FIGURES,
    GOLDEN_DAWN_GRADES,
    I_CHING_HEXAGRAMS,
    MASTER_NUMBERS,
    NUMEROLOGY_NUMBERS,
    chakra_correspondences,
    SEVEN_RAYS,
    TAROT_COURTS,
    TAROT_MAJORS,
    TAROT_SPREADS,
    TREE_OF_LIFE_PATHS,
    TREE_OF_LIFE_SEPHIROTH,
)
from ..registry import AstroRegistry

__all__ = ["register_esoteric_module"]


def register_esoteric_module(registry: AstroRegistry) -> None:
    """Attach esoteric datasets to the shared :class:`AstroRegistry`."""

    module = registry.register_module(
        "esoterica",
        metadata={
            "description": "Occult and initiatory correspondences layered onto natal analytics.",
            "datasets": [
                "golden_dawn_decans",
                "tree_of_life_sephiroth",
                "tree_of_life_paths",
                "alchemy_magnum_opus",
                "seven_rays_bailey",
                "golden_dawn_grade_ladder",
                "tarot_major_arcana",
                "tarot_court_cards",
                "tarot_spreads",
                "numerology_pythagorean",
                "numerology_master_numbers",
                "iching_king_wen",
                "elder_futhark_runes",
                "geomancy_figures_classical",
                "chakras_bihar_lineage",
            ],
        },
    )

    decans = module.register_submodule(
        "decans",
        metadata={
            "description": "Ten-degree divisions with Chaldean planetary rulers and tarot pips.",
            "division_degrees": 10,
            "total": len(DECANS),
        },
    )

    chaldean = decans.register_channel(
        "chaldean_order",
        metadata={
            "description": "Classical Chaldean sequence starting at 0° Aries.",
            "sources": [
                "Hermetic Order of the Golden Dawn — Book T (c. 1893)",
                "A. E. Waite — Pictorial Key to the Tarot (1910)",
            ],
        },
    )

    chaldean.register_subchannel(
        "golden_dawn_tarot",
        metadata={
            "description": "Golden Dawn pip card titles matched to the 36 decans.",
            "count": len(DECANS),
        },
        payload={"decans": [definition.to_payload() for definition in DECANS]},
    )

    kabbalah = module.register_submodule(
        "tree_of_life",
        metadata={
            "description": "Qabalistic sephiroth and paths with Golden Dawn attributions.",
            "sources": [
                "Hermetic Order of the Golden Dawn — 777 (1909)",
                "Dion Fortune — The Mystical Qabalah (1935)",
            ],
        },
    )
    sephiroth_channel = kabbalah.register_channel(
        "sephiroth",
        metadata={"count": len(TREE_OF_LIFE_SEPHIROTH)},
    )
    sephiroth_channel.register_subchannel(
        "golden_dawn",
        metadata={"description": "Ten sephiroth with planetary associations."},
        payload={"sephiroth": [item.to_payload() for item in TREE_OF_LIFE_SEPHIROTH]},
    )
    paths_channel = kabbalah.register_channel(
        "paths",
        metadata={"count": len(TREE_OF_LIFE_PATHS)},
    )
    paths_channel.register_subchannel(
        "attributions",
        metadata={"description": "Paths 11–32 with tarot and astrological keys."},
        payload={"paths": [item.to_payload() for item in TREE_OF_LIFE_PATHS]},
    )

    alchemy = module.register_submodule(
        "alchemy",
        metadata={
            "description": "Seven-stage Magnum Opus process from European laboratory texts.",
            "sources": [
                "Lyndy Abraham — A Dictionary of Alchemical Imagery (1998)",
                "Dennis William Hauck — The Complete Idiot's Guide to Alchemy (2008)",
            ],
        },
    )
    alchemy.register_channel(
        "operations",
        metadata={"stages": len(ALCHEMY_STAGES)},
    ).register_subchannel(
        "classical_sequence",
        metadata={"description": "Calcination through Coagulation."},
        payload={"stages": [stage.to_payload() for stage in ALCHEMY_STAGES]},
    )

    chakras = module.register_submodule(
        "chakras",
        metadata={
            "description": "Tantric chakra correspondences with planetary rulers and VCA-aligned domains.",
            "sources": [
                "Swami Satyananda Saraswati — Kundalini Tantra (1984)",
                "Anodea Judith — Wheels of Life (1987)",
            ],
        },
    )
    chakras.register_channel(
        "planetary_lineage",
        metadata={"count": len(chakra_correspondences())},
    ).register_subchannel(
        "bihar_school",
        metadata={
            "description": "Bihar School of Yoga chakra ↔ planetary ruler mapping with Mind/Body/Spirit weights.",
        },
        payload={"chakras": [chakra.to_payload() for chakra in chakra_correspondences()]},
    )

    rays = module.register_submodule(
        "seven_rays",
        metadata={
            "description": "Theosophical Seven Rays used in esoteric psychology overlays.",
            "sources": ["Alice A. Bailey — Esoteric Psychology I (1936)"],
        },
    )
    rays.register_channel(
        "bailey_lineage",
        metadata={"count": len(SEVEN_RAYS)},
    ).register_subchannel(
        "ray_profiles",
        metadata={"description": "Ray virtues, vices, and planetary rulers."},
        payload={"rays": [ray.to_payload() for ray in SEVEN_RAYS]},
    )

    orders = module.register_submodule(
        "initiatory_orders",
        metadata={
            "description": "Grades and ladders from ceremonial initiatory traditions.",
        },
    )
    orders.register_channel(
        "golden_dawn",
        metadata={
            "description": "Grade structure of the Hermetic Order of the Golden Dawn.",
            "sources": ["Israel Regardie — The Golden Dawn (1937)"],
        },
    ).register_subchannel(
        "grade_ladder",
        metadata={"count": len(GOLDEN_DAWN_GRADES)},
        payload={"grades": [grade.to_payload() for grade in GOLDEN_DAWN_GRADES]},
    )

    tarot = module.register_submodule(
        "tarot",
        metadata={
            "description": "Major arcana, court structures, and spreads extending decan overlays.",
            "sources": [
                "Hermetic Order of the Golden Dawn — Book T (c. 1893)",
                "Arthur Edward Waite — The Pictorial Key to the Tarot (1910)",
            ],
        },
    )
    tarot.register_channel(
        "majors",
        metadata={"count": len(TAROT_MAJORS)},
    ).register_subchannel(
        "golden_dawn_paths",
        metadata={
            "description": "Major arcana with Hebrew letters and path attributions."
        },
        payload={"cards": [card.to_payload() for card in TAROT_MAJORS]},
    )
    tarot.register_channel(
        "courts",
        metadata={"count": len(TAROT_COURTS)},
    ).register_subchannel(
        "book_t_quadrants",
        metadata={
            "description": "Court cards with elemental qualities and zodiacal spans."
        },
        payload={"courts": [card.to_payload() for card in TAROT_COURTS]},
    )
    tarot.register_channel(
        "spreads",
        metadata={"count": len(TAROT_SPREADS)},
    ).register_subchannel(
        "documented_spreads",
        metadata={
            "description": "Classic spreads referenced in Golden Dawn and Waite materials."
        },
        payload={"spreads": [spread.to_payload() for spread in TAROT_SPREADS]},
    )

    adapters = module.register_submodule(
        "adapters",
        metadata={
            "description": "Optional tarot and numerology prompts mapped from natal data.",
            "notes": "Helpers surface meditative overlays only when explicitly requested.",
        },
    )
    adapters.register_channel(
        "optional_tools",
        metadata={
            "tarot_mapper": "astroengine.esoteric.adapters.tarot_mapper",
            "numerology_mapper": "astroengine.esoteric.adapters.numerology_mapper",
        },
    ).register_subchannel(
        "tarot_numerology",
        metadata={
            "description": "Expose optional tarot and numerology adapters with disclaimers.",
            "tests": ["tests/test_esoteric_adapters.py"],
        },
        payload={
            "tarot_mapper": "astroengine.esoteric.adapters.tarot_mapper",
            "numerology_mapper": "astroengine.esoteric.adapters.numerology_mapper",
        },
    )

    numerology = module.register_submodule(
        "numerology",
        metadata={
            "description": "Pythagorean numerology keyed to planetary rulers.",
            "sources": [
                "Cheiro — Cheiro's Book of Numbers (1926)",
                "Florence Campbell — Your Days Are Numbered (1931)",
            ],
        },
    )
    numbers_channel = numerology.register_channel(
        "digits",
        metadata={"count": len(NUMEROLOGY_NUMBERS)},
    )
    numbers_channel.register_subchannel(
        "pythagorean",
        metadata={"description": "Digits 0–9 with planetary keywords."},
        payload={"numbers": [number.to_payload() for number in NUMEROLOGY_NUMBERS]},
    )
    numbers_channel.register_subchannel(
        "master_numbers",
        metadata={
            "description": "Master numbers emphasised in 20th century numerology."
        },
        payload={"numbers": [number.to_payload() for number in MASTER_NUMBERS]},
    )

    divination = module.register_submodule(
        "oracular_systems",
        metadata={"description": "Cross-cultural oracles layered alongside astrology."},
    )
    divination.register_channel(
        "i_ching",
        metadata={
            "description": "King Wen sequence for the Zhouyi",
            "count": len(I_CHING_HEXAGRAMS),
            "sources": ["Richard Wilhelm — The I Ching or Book of Changes (1923)"],
        },
    ).register_subchannel(
        "king_wen_sequence",
        metadata={"description": "Hexagrams with Chinese names and thematic keywords."},
        payload={
            "hexagrams": [hexagram.to_payload() for hexagram in I_CHING_HEXAGRAMS]
        },
    )
    divination.register_channel(
        "runes",
        metadata={
            "description": "Elder Futhark rune row for northern European work.",
            "count": len(ELDER_FUTHARK_RUNES),
            "sources": [
                "Stephen Flowers — Futhark: A Handbook of Rune Magic (1984)",
                "Diana L. Paxson — Taking Up the Runes (2005)",
            ],
        },
    ).register_subchannel(
        "elder_futhark",
        metadata={"description": "Twenty-four runes with phonetic and elemental keys."},
        payload={"runes": [rune.to_payload() for rune in ELDER_FUTHARK_RUNES]},
    )
    divination.register_channel(
        "geomancy",
        metadata={
            "description": "Renaissance geomantic figures applied alongside horary astrology.",
            "count": len(GEOMANTIC_FIGURES),
            "sources": [
                "Heinrich Cornelius Agrippa — De Occulta Philosophia (1533)",
                "John Michael Greer — The Art and Practice of Geomancy (1999)",
            ],
        },
    ).register_subchannel(
        "agrippa_sequence",
        metadata={
            "description": "Sixteen figures with planetary and zodiacal rulers in classical order."
        },
        payload={"figures": [figure.to_payload() for figure in GEOMANTIC_FIGURES]},
    )
