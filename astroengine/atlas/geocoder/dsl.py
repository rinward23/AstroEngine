"""Address parsing DSL powering the atlas geocoder."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterator, Mapping, MutableMapping, Sequence

from .transliterate import normalize_token, transliterate

__all__ = [
    "AddressComponents",
    "AddressParser",
    "GrammarDefinition",
    "compile_grammar",
    "load_builtin_parser",
]


class AddressComponents(MutableMapping[str, str]):
    """Dictionary-like holder for parsed address components."""

    _data: dict[str, str]

    def __init__(self, initial: Mapping[str, str] | None = None) -> None:
        self._data = dict(initial or {})

    def __getitem__(self, key: str) -> str:
        return self._data[key]

    def __setitem__(self, key: str, value: str) -> None:
        self._data[key] = value

    def __delitem__(self, key: str) -> None:
        del self._data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def normalised_query(self) -> str:
        """Return a canonical query combining the parsed components."""

        parts: list[str] = []
        for key in ("house_number", "street", "city", "admin1", "country"):
            value = self._data.get(key)
            if value:
                parts.append(value)
        if not parts and "remainder" in self._data:
            parts.append(self._data["remainder"])
        return " ".join(parts)

    def as_dict(self) -> dict[str, str]:
        return dict(self._data)


@dataclass(frozen=True)
class GrammarDefinition:
    """In-memory representation of an address parsing grammar."""

    language: str
    patterns: Sequence[str]


@dataclass(frozen=True)
class _CompiledPattern:
    language: str
    regex: re.Pattern[str]
    tokens: Sequence[str]


class AddressParser:
    """Parser compiled from the DSL grammar definitions."""

    def __init__(self, patterns: Sequence[_CompiledPattern]) -> None:
        self._patterns = list(patterns)

    def parse(self, text: str, *, language: str | None = None) -> AddressComponents:
        """Parse ``text`` returning structured components.

        When ``language`` is provided only patterns tagged with the language are
        evaluated. The parser automatically attempts transliteration to improve
        matching across Unicode scripts.
        """

        search_space: Sequence[_CompiledPattern]
        if language is None:
            search_space = self._patterns
        else:
            search_space = [p for p in self._patterns if p.language == language]

        candidates = [" ".join(text.split())]
        transliterated = transliterate(text, aggressive=True)
        if transliterated not in candidates:
            candidates.append(" ".join(transliterated.split()))

        for candidate in candidates:
            for pattern in search_space:
                match = pattern.regex.fullmatch(candidate)
                if not match:
                    continue
                data = AddressComponents(
                    {token: match.group(token).strip() for token in pattern.tokens if match.group(token)}
                )
                data["language"] = pattern.language
                if "remainder" not in data:
                    leftovers = match.groupdict().get("remainder")
                    if leftovers:
                        data["remainder"] = leftovers.strip()
                return data

        normalised = normalize_token(text)
        fallback = AddressComponents({})
        if normalised:
            fallback["remainder"] = normalised
        if language:
            fallback["language"] = language
        return fallback


_TOKEN_PATTERN = re.compile(r"\{\{\s*(?P<token>[a-zA-Z0-9_]+)\s*\}\}")
_OPTIONAL_PATTERN = re.compile(r"\[(?P<body>[^\[\]]+)\]")
_ALLOWED_TOKENS = {
    "house_number",
    "street",
    "city",
    "admin1",
    "admin2",
    "postal_code",
    "country",
    "remainder",
}


def _escape_literal(text: str) -> str:
    return re.escape(text)


def _token_regex(token: str) -> str:
    if token == "postal_code":
        return r"(?P<postal_code>[0-9A-Za-z\- ]{2,12})"
    if token == "house_number":
        return r"(?P<house_number>[0-9A-Za-z\-/]{1,10})"
    if token == "remainder":
        return r"(?P<remainder>.+)"
    return rf"(?P<{token}>[^,]+)"


def _compile_pattern(language: str, pattern: str) -> _CompiledPattern:
    tokens: list[str] = []

    def replace_optional(match: re.Match[str]) -> str:
        inner = match.group("body")
        return f"(?:{_compile_body(inner)})?"

    def _compile_body(body: str) -> str:
        parts: list[str] = []
        index = 0
        while index < len(body):
            token_match = _TOKEN_PATTERN.search(body, index)
            if not token_match:
                literal = body[index:]
                parts.append(_escape_literal(literal))
                break
            if token_match.start() > index:
                literal = body[index:token_match.start()]
                parts.append(_escape_literal(literal))
            token = token_match.group("token")
            if token not in _ALLOWED_TOKENS:
                raise ValueError(f"Unknown token '{token}' in pattern '{pattern}'")
            tokens.append(token)
            parts.append(_token_regex(token))
            index = token_match.end()
        return "".join(parts)

    pattern_with_optional = _OPTIONAL_PATTERN.sub(replace_optional, pattern)
    regex_body = _compile_body(pattern_with_optional)
    regex = re.compile(rf"^{regex_body}$", re.IGNORECASE)
    return _CompiledPattern(language=language, regex=regex, tokens=tuple(dict.fromkeys(tokens)))


def compile_grammar(definition: Sequence[GrammarDefinition]) -> AddressParser:
    """Compile the DSL definition into an :class:`AddressParser`."""

    patterns: list[_CompiledPattern] = []
    for grammar in definition:
        for pattern in grammar.patterns:
            patterns.append(_compile_pattern(grammar.language, pattern))
    return AddressParser(patterns)


_BUILTIN_GRAMMAR: list[GrammarDefinition] = [
    GrammarDefinition(
        language="en",
        patterns=[
            "{{house_number}} {{street}}, {{city}}, {{admin1}}, {{country}}",
            "{{city}}, {{admin1}}, {{country}}",
            "{{city}}, {{country}}",
        ],
    ),
    GrammarDefinition(
        language="es",
        patterns=[
            "{{street}} {{house_number}}, {{city}}, {{admin1}}, {{country}}",
            "{{city}}, {{admin1}}, {{country}}",
        ],
    ),
    GrammarDefinition(
        language="fr",
        patterns=[
            "{{house_number}} {{street}}, {{postal_code}} {{city}}, {{country}}",
            "{{city}}, {{country}}",
        ],
    ),
    GrammarDefinition(
        language="de",
        patterns=[
            "{{street}} {{house_number}}, {{postal_code}} {{city}}, {{country}}",
            "{{city}}, {{country}}",
        ],
    ),
    GrammarDefinition(
        language="ru",
        patterns=[
            "{{country}}, {{admin1}}, {{city}}, {{street}} {{house_number}}",
            "{{city}}, {{country}}",
        ],
    ),
]


def load_builtin_parser() -> AddressParser:
    """Return the parser compiled from the bundled grammar definitions."""

    return compile_grammar(_BUILTIN_GRAMMAR)
