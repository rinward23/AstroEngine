"""Lightweight transliteration helpers used by the atlas geocoder."""

from __future__ import annotations

import unicodedata
from functools import lru_cache
from typing import Iterable

# Core mappings assembled from transliteration tables for Cyrillic and Greek.
# The mapping is intentionally conservative so that the DSL can match both the
# transliterated and native spellings when present in offline indices.
CYRILLIC_MAP: dict[str, str] = {
    "А": "A",
    "Б": "B",
    "В": "V",
    "Г": "G",
    "Д": "D",
    "Е": "E",
    "Ё": "E",
    "Ж": "Zh",
    "З": "Z",
    "И": "I",
    "Й": "I",
    "К": "K",
    "Л": "L",
    "М": "M",
    "Н": "N",
    "О": "O",
    "П": "P",
    "Р": "R",
    "С": "S",
    "Т": "T",
    "У": "U",
    "Ф": "F",
    "Х": "Kh",
    "Ц": "Ts",
    "Ч": "Ch",
    "Ш": "Sh",
    "Щ": "Shch",
    "Ы": "Y",
    "Э": "E",
    "Ю": "Yu",
    "Я": "Ya",
    "Ъ": "",
    "Ь": "",
}

GREEK_MAP: dict[str, str] = {
    "Α": "A",
    "Β": "V",
    "Γ": "G",
    "Δ": "D",
    "Ε": "E",
    "Ζ": "Z",
    "Η": "I",
    "Θ": "Th",
    "Ι": "I",
    "Κ": "K",
    "Λ": "L",
    "Μ": "M",
    "Ν": "N",
    "Ξ": "X",
    "Ο": "O",
    "Π": "P",
    "Ρ": "R",
    "Σ": "S",
    "Τ": "T",
    "Υ": "Y",
    "Φ": "F",
    "Χ": "Ch",
    "Ψ": "Ps",
    "Ω": "O",
}

SCRIPT_MAP: dict[str, str] = {}
SCRIPT_MAP.update({k: v for k, v in CYRILLIC_MAP.items()})
SCRIPT_MAP.update({k.lower(): v.lower() for k, v in CYRILLIC_MAP.items()})
SCRIPT_MAP.update({k: v for k, v in GREEK_MAP.items()})
SCRIPT_MAP.update({k.lower(): v.lower() for k, v in GREEK_MAP.items()})


def _strip_diacritics(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


@lru_cache(maxsize=8192)
def transliterate(text: str, *, aggressive: bool = False) -> str:
    """Return a Latin transliteration of ``text``.

    The helper focuses on high signal conversions that benefit fuzzy searches in
    the gazetteer. Characters without a mapping are passed through. When
    ``aggressive`` is ``True`` the function also strips combining marks via
    Unicode decomposition.
    """

    if not text:
        return ""

    output: list[str] = []
    for ch in text:
        mapped = SCRIPT_MAP.get(ch)
        if mapped is not None:
            output.append(mapped)
            continue
        output.append(ch)

    transliterated = "".join(output)
    if aggressive:
        transliterated = _strip_diacritics(transliterated)
    return transliterated


def normalize_token(text: str) -> str:
    """Return an ASCII token suitable for search indexes."""

    transliterated = transliterate(text, aggressive=True)
    decomposed = unicodedata.normalize("NFKD", transliterated)
    ascii_only = []
    for ch in decomposed:
        if ord(ch) < 128 and (ch.isalnum() or ch.isspace()):
            ascii_only.append(ch)
    return " ".join("".join(ascii_only).lower().split())


def bulk_transliterate(tokens: Iterable[str]) -> list[str]:
    """Apply :func:`transliterate` to many tokens efficiently."""

    return [transliterate(token, aggressive=True) for token in tokens]
