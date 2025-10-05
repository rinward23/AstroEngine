"""Parser for the Lots mini-DSL used by the sandbox and API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Collection, List, Sequence, Tuple, Union

Number = Union[int, float]


class FormulaSyntaxError(ValueError):
    """Raised when a formula cannot be parsed safely."""


@dataclass(frozen=True)
class Term:
    """Single term in a Lots expression."""

    kind: str  # ``"num"`` or ``"sym"``
    value: Union[str, float]


def _tokenize(expr: str) -> List[str]:
    tokens = expr.replace("\t", " ").split()
    if not tokens:
        raise FormulaSyntaxError("Formula must not be empty")
    return tokens


def _is_symbol(token: str) -> bool:
    return token.replace("_", "").isalnum()


def parse_formula(expr: str) -> List[Tuple[str, Term]]:
    """Parse ``expr`` into a sequence of ``(op, Term)`` pairs.

    The parser only understands ``+`` and ``-`` operators and treats every
    non-numeric token as an identifier consisting of alphanumeric characters
    or underscores. Any other character results in :class:`FormulaSyntaxError`.
    """

    tokens = _tokenize(expr)
    result: List[Tuple[str, Term]] = []
    op = "+"
    expect_term = True

    for token in tokens:
        if expect_term:
            if token in {"+", "-"}:
                raise FormulaSyntaxError("Formula cannot have consecutive operators")
            try:
                value = float(token)
            except ValueError:
                if not _is_symbol(token):
                    raise FormulaSyntaxError(f"Invalid symbol '{token}'")
                term = Term("sym", token)
            else:
                term = Term("num", value)
            result.append((op, term))
            expect_term = False
        else:
            if token not in {"+", "-"}:
                raise FormulaSyntaxError("Expected '+' or '-' between terms")
            op = token
            expect_term = True

    if expect_term:
        raise FormulaSyntaxError("Formula cannot end with an operator")

    return result


def extract_symbols(expr: str) -> List[str]:
    """Return symbol names referenced in ``expr`` preserving order."""

    symbols: List[str] = []
    for _, term in parse_formula(expr):
        if term.kind == "sym":
            symbols.append(str(term.value))
    return symbols


def validate_formula(expr: str, allowed_symbols: Collection[str] | None = None) -> Sequence[Tuple[str, Term]]:
    """Parse ``expr`` and optionally ensure identifiers belong to ``allowed_symbols``.

    ``allowed_symbols`` comparison is case-insensitive.
    """

    terms = parse_formula(expr)
    if allowed_symbols is None:
        return terms

    normalized = {symbol.lower() for symbol in allowed_symbols}
    invalid = {
        str(term.value)
        for _, term in terms
        if term.kind == "sym" and term.value.lower() not in normalized
    }
    if invalid:
        ordered = sorted(invalid)
        raise FormulaSyntaxError(f"Unknown symbols: {', '.join(ordered)}")
    return terms


__all__ = [
    "FormulaSyntaxError",
    "Number",
    "Term",
    "extract_symbols",
    "parse_formula",
    "validate_formula",
]

