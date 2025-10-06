"""Domain specific language for Arabic Lots expressions."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass

__all__ = [
    "Add",
    "Arc",
    "CompiledProgram",
    "Expr",
    "IfDay",
    "LotDef",
    "LotProgram",
    "Number",
    "Ref",
    "Sub",
    "Wrap",
    "compile_program",
    "detect_cycles",
    "parse_lot_defs",
]


@dataclass(frozen=True)
class Expr:
    """Base class for expression nodes."""


@dataclass(frozen=True)
class Number(Expr):
    value: float


@dataclass(frozen=True)
class Ref(Expr):
    name: str


@dataclass(frozen=True)
class Add(Expr):
    left: Expr
    right: Expr


@dataclass(frozen=True)
class Sub(Expr):
    left: Expr
    right: Expr


@dataclass(frozen=True)
class Arc(Expr):
    first: Expr
    second: Expr


@dataclass(frozen=True)
class Wrap(Expr):
    value: Expr


@dataclass(frozen=True)
class IfDay(Expr):
    day_expr: Expr
    night_expr: Expr


@dataclass(frozen=True)
class LotDef:
    name: str
    expr: Expr


@dataclass(frozen=True)
class LotProgram:
    definitions: Sequence[LotDef]

    def names(self) -> list[str]:
        return [definition.name for definition in self.definitions]


@dataclass(frozen=True)
class CompiledProgram:
    definitions: dict[str, Expr]
    order: Sequence[str]
    dependencies: dict[str, set[str]]


class _Token:
    __slots__ = ("kind", "value")

    def __init__(self, kind: str, value: str):
        self.kind = kind
        self.value = value

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"Token({self.kind!r}, {self.value!r})"


_KEYWORDS = {"arc", "wrap", "if_day", "deg", "mean"}
_WHITESPACE = {" ", "\t", "\r", "\n"}


class _Tokenizer:
    def __init__(self, text: str) -> None:
        self._text = text
        self._length = len(text)
        self._index = 0

    def __iter__(self) -> Iterator[_Token]:
        while True:
            token = self._next_token()
            if token is None:
                break
            yield token

    def _next_token(self) -> _Token | None:
        self._skip_whitespace()
        if self._index >= self._length:
            return None
        char = self._text[self._index]
        if char.isalpha() or char == "_":
            return self._identifier()
        if char.isdigit() or char == ".":
            return self._number()
        self._index += 1
        if char in "+-(),=":
            return _Token(char, char)
        raise ValueError(f"Unexpected character: {char!r}")

    def _skip_whitespace(self) -> None:
        while self._index < self._length and self._text[self._index] in _WHITESPACE:
            self._index += 1

    def _identifier(self) -> _Token:
        start = self._index
        self._index += 1
        while (
            self._index < self._length
            and (self._text[self._index].isalnum() or self._text[self._index] == "_")
        ):
            self._index += 1
        value = self._text[start : self._index]
        return _Token("IDENT", value)

    def _number(self) -> _Token:
        start = self._index
        dot_seen = False
        while self._index < self._length:
            char = self._text[self._index]
            if char == ".":
                if dot_seen:
                    break
                dot_seen = True
            elif not char.isdigit():
                break
            self._index += 1
        value = self._text[start : self._index]
        return _Token("NUMBER", value)


class _Parser:
    def __init__(self, tokens: Iterable[_Token]):
        self._tokens = list(tokens)
        self._position = 0
        self._length = len(self._tokens)

    def parse(self) -> LotProgram:
        definitions: list[LotDef] = []
        while not self._at_end:
            definition = self._definition()
            definitions.append(definition)
        return LotProgram(tuple(definitions))

    @property
    def _at_end(self) -> bool:
        return self._position >= self._length

    def _peek(self) -> _Token | None:
        if self._position < self._length:
            return self._tokens[self._position]
        return None

    def _consume(self, expected: str | None = None) -> _Token:
        if self._position >= self._length:
            raise ValueError("Unexpected end of input")
        token = self._tokens[self._position]
        if expected is not None and token.kind != expected and token.value != expected:
            raise ValueError(f"Expected {expected!r} but found {token.value!r}")
        self._position += 1
        return token

    def _definition(self) -> LotDef:
        name_token = self._consume("IDENT")
        self._consume("=")
        expr = self._expression()
        return LotDef(name_token.value, expr)

    def _expression(self) -> Expr:
        node = self._term()
        while True:
            token = self._peek()
            if token is None or token.value not in {"+", "-"}:
                break
            op = token.value
            self._consume()
            right = self._term()
            if op == "+":
                node = Add(node, right)
            else:
                node = Sub(node, right)
        return node

    def _term(self) -> Expr:
        token = self._peek()
        if token is None:
            raise ValueError("Unexpected end of input")
        if token.kind == "NUMBER":
            self._consume()
            return Number(float(token.value))
        if token.kind == "IDENT":
            self._consume()
            if token.value in _KEYWORDS:
                return self._function(token.value)
            return Ref(token.value)
        if token.value == "(":
            self._consume()
            expr = self._expression()
            self._consume(")")
            return expr
        raise ValueError(f"Unexpected token {token.value!r}")

    def _function(self, name: str) -> Expr:
        if name == "deg":
            self._consume("(")
            value = self._expression()
            self._consume(")")
            return value
        if name == "arc":
            self._consume("(")
            first = self._expression()
            self._consume(",")
            second = self._expression()
            self._consume(")")
            return Arc(first, second)
        if name == "wrap":
            self._consume("(")
            inner = self._expression()
            self._consume(")")
            return Wrap(inner)
        if name == "if_day":
            self._consume("(")
            day_expr = self._expression()
            self._consume(",")
            night_expr = self._expression()
            self._consume(")")
            return IfDay(day_expr, night_expr)
        if name == "mean":
            raise ValueError("mean() is not supported in this implementation")
        raise ValueError(f"Unsupported function {name!r}")


def parse_lot_defs(text: str) -> LotProgram:
    """Parse ``text`` into a :class:`LotProgram`."""

    tokens = _Tokenizer(text)
    parser = _Parser(tokens)
    return parser.parse()


def _references(expr: Expr) -> set[str]:
    if isinstance(expr, Ref):
        return {expr.name}
    if isinstance(expr, Number):
        return set()
    if isinstance(expr, Add):
        return _references(expr.left) | _references(expr.right)
    if isinstance(expr, Sub):
        return _references(expr.left) | _references(expr.right)
    if isinstance(expr, Arc):
        return _references(expr.first) | _references(expr.second)
    if isinstance(expr, Wrap):
        return _references(expr.value)
    if isinstance(expr, IfDay):
        return _references(expr.day_expr) | _references(expr.night_expr)
    raise TypeError(f"Unsupported expression node {type(expr)!r}")


def detect_cycles(program: LotProgram) -> list[list[str]]:
    """Return dependency cycles detected in ``program``."""

    dependencies: dict[str, set[str]] = {}
    defined = set(program.names())
    for definition in program.definitions:
        refs = {ref for ref in _references(definition.expr) if ref in defined}
        dependencies[definition.name] = refs

    cycles: list[list[str]] = []
    temp: set[str] = set()
    perm: set[str] = set()
    stack: list[str] = []

    def visit(name: str) -> None:
        if name in perm:
            return
        if name in temp:
            cycle_start = stack.index(name)
            cycles.append(stack[cycle_start:] + [name])
            return
        temp.add(name)
        stack.append(name)
        for dep in dependencies.get(name, set()):
            visit(dep)
        temp.remove(name)
        perm.add(name)
        stack.pop()

    for name in program.names():
        visit(name)

    return cycles


def compile_program(program: LotProgram) -> CompiledProgram:
    """Compile ``program`` into a topologically sorted representation."""

    seen: set[str] = set()
    order: list[str] = []
    dependencies: dict[str, set[str]] = {}
    defined = {definition.name for definition in program.definitions}

    for definition in program.definitions:
        if definition.name in seen:
            raise ValueError(f"Duplicate lot definition: {definition.name}")
        seen.add(definition.name)
        refs = {ref for ref in _references(definition.expr) if ref in defined}
        dependencies[definition.name] = refs

    cycles = detect_cycles(program)
    if cycles:
        raise ValueError(f"Cyclic dependencies detected: {cycles}")

    remaining = set(seen)
    resolved: set[str] = set()
    while remaining:
        progress = False
        for name in list(remaining):
            deps = dependencies[name]
            if deps.issubset(resolved):
                order.append(name)
                resolved.add(name)
                remaining.remove(name)
                progress = True
        if not progress:
            raise ValueError("Cannot resolve dependency order")

    definitions = {definition.name: definition.expr for definition in program.definitions}
    return CompiledProgram(definitions, tuple(order), dependencies)
