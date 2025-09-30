"""Parser for the Ruleset DSL described in SPEC-12."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple

__all__ = [
    "DSLParseError",
    "BooleanBinaryOp",
    "BooleanNot",
    "BooleanNode",
    "BinaryOp",
    "CallExpr",
    "Comparison",
    "Expr",
    "Identifier",
    "Number",
    "RuleNode",
    "UnaryOp",
    "parse_rule",
    "parse_rules",
]


class DSLParseError(ValueError):
    """Exception raised when the DSL input cannot be parsed."""

    def __init__(self, message: str, line: int, column: int) -> None:
        super().__init__(f"{message} (line {line}, column {column})")
        self.message = message
        self.line = line
        self.column = column


@dataclass(frozen=True)
class Token:
    """Representation of a lexical token."""

    type: str
    value: object
    line: int
    column: int


class Node:
    """Base class for AST nodes."""

    __slots__ = ()


class Expr(Node):
    """Base class for arithmetic/value expressions."""

    __slots__ = ()


class BooleanNode(Node):
    """Base class for boolean expressions."""

    __slots__ = ()


@dataclass(frozen=True)
class Number(Expr):
    value: float


@dataclass(frozen=True)
class Identifier(Expr):
    name: str


@dataclass(frozen=True)
class CallExpr(Expr, BooleanNode):
    name: str
    args: Tuple[Expr, ...]


@dataclass(frozen=True)
class UnaryOp(Expr):
    op: str
    operand: Expr


@dataclass(frozen=True)
class BinaryOp(Expr):
    left: Expr
    op: str
    right: Expr


@dataclass(frozen=True)
class Comparison(BooleanNode):
    left: Expr
    op: str
    right: Expr


@dataclass(frozen=True)
class BooleanBinaryOp(BooleanNode):
    left: BooleanNode
    op: str
    right: BooleanNode


@dataclass(frozen=True)
class BooleanNot(BooleanNode):
    operand: BooleanNode


@dataclass(frozen=True)
class RuleNode(Node):
    name: str
    when: BooleanNode
    then: Expr
    weight: float
    tags: Tuple[str, ...]


_KEYWORDS = {
    "rule": "RULE",
    "when": "WHEN",
    "then": "THEN",
    "weight": "WEIGHT",
    "tags": "TAGS",
    "and": "AND",
    "or": "OR",
    "not": "NOT",
}

_COMPARATORS = {
    "==": "EQ",
    "!=": "NE",
    "<": "LT",
    "<=": "LE",
    ">": "GT",
    ">=": "GE",
}

_PUNCTUATION = {
    "{": "LBRACE",
    "}": "RBRACE",
    "[": "LBRACKET",
    "]": "RBRACKET",
    "(": "LPAREN",
    ")": "RPAREN",
    ":": "COLON",
    ",": "COMMA",
    "+": "PLUS",
    "-": "MINUS",
    "*": "STAR",
    "/": "SLASH",
}


class Tokenizer:
    """Convert a DSL string into a stream of tokens."""

    def __init__(self, source: str) -> None:
        self._source = source
        self._length = len(source)
        self._index = 0
        self._line = 1
        self._column = 1

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []
        while not self._is_at_end:
            ch = self._peek()
            if ch.isspace():
                self._consume_whitespace()
                continue
            if ch == "#":
                self._consume_comment()
                continue
            if ch.isalpha() or ch == "_":
                tokens.append(self._read_identifier())
                continue
            if ch.isdigit() or (ch == "." and self._peek_next().isdigit()):
                tokens.append(self._read_number())
                continue
            if ch in {'"', "'"}:
                tokens.append(self._read_string())
                continue
            token = self._read_operator()
            tokens.append(token)
        tokens.append(Token("EOF", "", self._line, self._column))
        return tokens

    @property
    def _is_at_end(self) -> bool:
        return self._index >= self._length

    def _peek(self) -> str:
        if self._is_at_end:
            return "\0"
        return self._source[self._index]

    def _peek_next(self) -> str:
        if self._index + 1 >= self._length:
            return "\0"
        return self._source[self._index + 1]

    def _advance(self) -> str:
        ch = self._source[self._index]
        self._index += 1
        if ch == "\n":
            self._line += 1
            self._column = 1
        else:
            self._column += 1
        return ch

    def _consume_whitespace(self) -> None:
        while not self._is_at_end and self._peek().isspace():
            self._advance()

    def _consume_comment(self) -> None:
        while not self._is_at_end and self._peek() != "\n":
            self._advance()

    def _read_identifier(self) -> Token:
        start_line, start_col = self._line, self._column
        value_chars: List[str] = []
        while not self._is_at_end and (self._peek().isalnum() or self._peek() == "_"):
            value_chars.append(self._advance())
        text = "".join(value_chars)
        token_type = _KEYWORDS.get(text, "IDENT")
        value: object = text
        return Token(token_type, value, start_line, start_col)

    def _read_number(self) -> Token:
        start_line, start_col = self._line, self._column
        start_index = self._index
        has_dot = False
        while not self._is_at_end:
            ch = self._peek()
            if ch.isdigit():
                self._advance()
            elif ch == "." and not has_dot:
                has_dot = True
                self._advance()
            elif ch in {"e", "E"}:
                self._advance()
                if self._peek() in {"+", "-"}:
                    self._advance()
                digits = 0
                while self._peek().isdigit():
                    self._advance()
                    digits += 1
                if digits == 0:
                    raise DSLParseError("Invalid exponent in number literal", self._line, self._column)
            else:
                break
        text = self._source[start_index:self._index]
        try:
            number = float(text)
        except ValueError as exc:  # pragma: no cover - safeguard
            raise DSLParseError("Invalid number literal", start_line, start_col) from exc
        return Token("NUMBER", number, start_line, start_col)

    def _read_string(self) -> Token:
        quote = self._advance()
        start_line, start_col = self._line, self._column - 1
        value_chars: List[str] = []
        while not self._is_at_end:
            ch = self._advance()
            if ch == quote:
                break
            if ch == "\\":
                if self._is_at_end:
                    raise DSLParseError("Unterminated string literal", self._line, self._column)
                esc = self._advance()
                if esc == "n":
                    value_chars.append("\n")
                elif esc == "t":
                    value_chars.append("\t")
                elif esc == "\"":
                    value_chars.append("\"")
                elif esc == "'":
                    value_chars.append("'")
                elif esc == "\\":
                    value_chars.append("\\")
                else:
                    raise DSLParseError(f"Unsupported escape '{esc}'", self._line, self._column)
            else:
                value_chars.append(ch)
        else:
            raise DSLParseError("Unterminated string literal", start_line, start_col)
        return Token("STRING", "".join(value_chars), start_line, start_col)

    def _read_operator(self) -> Token:
        start_line, start_col = self._line, self._column
        ch = self._advance()
        two_char = ch + self._peek()
        if two_char in _COMPARATORS:
            self._advance()
            token_type = _COMPARATORS[two_char]
            return Token(token_type, two_char, start_line, start_col)
        if ch in _COMPARATORS:
            token_type = _COMPARATORS[ch]
            return Token(token_type, ch, start_line, start_col)
        if ch in _PUNCTUATION:
            token_type = _PUNCTUATION[ch]
            return Token(token_type, ch, start_line, start_col)
        raise DSLParseError(f"Unexpected character '{ch}'", start_line, start_col)


class Parser:
    """Recursive descent parser for the Ruleset DSL."""

    def __init__(self, tokens: Sequence[Token]) -> None:
        self._tokens = tokens
        self._position = 0

    def parse_rule(self) -> RuleNode:
        self._consume("RULE", "Expected 'rule'")
        name_token = self._consume("IDENT", "Expected rule name")
        self._consume("LBRACE", "Expected '{'")
        rule = self._parse_rule_body(name_token.value)
        self._consume("RBRACE", "Expected '}'")
        return rule

    def parse_rules(self) -> List[RuleNode]:
        rules: List[RuleNode] = []
        while not self._check("EOF"):
            rules.append(self.parse_rule())
        self._consume("EOF", "Unexpected trailing tokens")
        return rules

    def _parse_rule_body(self, name: str) -> RuleNode:
        self._consume("WHEN", "Expected 'when' section")
        self._consume("COLON", "Expected ':' after 'when'")
        when_expr = self._parse_bool_expr()
        self._consume("COMMA", "Expected ',' after 'when' expression")
        self._consume("THEN", "Expected 'then' section")
        self._consume("COLON", "Expected ':' after 'then'")
        then_expr = self._parse_expr()
        self._consume("COMMA", "Expected ',' after 'then' expression")
        self._consume("WEIGHT", "Expected 'weight' section")
        self._consume("COLON", "Expected ':' after 'weight'")
        weight_token = self._consume("NUMBER", "Weight must be a number")
        tags: Tuple[str, ...] = ()
        if self._match("COMMA"):
            if self._match("TAGS"):
                self._consume("COLON", "Expected ':' after 'tags'")
                tags = self._parse_tags()
                self._match("COMMA")  # optional trailing comma
            else:
                token = self._previous
                self._error(token, "Expected 'tags' section")
        return RuleNode(name=name, when=when_expr, then=then_expr, weight=float(weight_token.value), tags=tags)

    def _parse_tags(self) -> Tuple[str, ...]:
        self._consume("LBRACKET", "Expected '[' to start tag list")
        tags: List[str] = []
        if not self._check("RBRACKET"):
            while True:
                if self._check("STRING"):
                    token = self._advance()
                    tags.append(str(token.value))
                elif self._check("IDENT"):
                    token = self._advance()
                    tags.append(str(token.value))
                else:
                    token = self._peek()
                    self._error(token, "Tags must be string literals or identifiers")
                if not self._match("COMMA"):
                    break
        self._consume("RBRACKET", "Expected ']' after tags")
        return tuple(tags)

    def _parse_bool_expr(self) -> BooleanNode:
        return self._parse_bool_or()

    def _parse_bool_or(self) -> BooleanNode:
        expr = self._parse_bool_and()
        while self._match("OR"):
            right = self._parse_bool_and()
            expr = BooleanBinaryOp(expr, "or", right)
        return expr

    def _parse_bool_and(self) -> BooleanNode:
        expr = self._parse_bool_not()
        while self._match("AND"):
            right = self._parse_bool_not()
            expr = BooleanBinaryOp(expr, "and", right)
        return expr

    def _parse_bool_not(self) -> BooleanNode:
        if self._match("NOT"):
            operand = self._parse_bool_not()
            return BooleanNot(operand)
        return self._parse_bool_atom()

    def _parse_bool_atom(self) -> BooleanNode:
        if self._match("LPAREN"):
            expr = self._parse_bool_expr()
            self._consume("RPAREN", "Expected ')' after boolean expression")
            return expr
        expr = self._parse_expr()
        if self._match("EQ", "NE", "LT", "LE", "GT", "GE"):
            operator = self._previous
            right = self._parse_expr()
            return Comparison(expr, operator.value, right)
        if isinstance(expr, CallExpr):
            return expr
        token = self._previous
        self._error(token, "Boolean expression must be a comparison or predicate call")
        raise AssertionError("unreachable")

    def _parse_expr(self) -> Expr:
        return self._parse_term()

    def _parse_term(self) -> Expr:
        expr = self._parse_factor()
        while self._match("PLUS", "MINUS"):
            operator = self._previous
            right = self._parse_factor()
            expr = BinaryOp(expr, str(operator.value), right)
        return expr

    def _parse_factor(self) -> Expr:
        expr = self._parse_unary()
        while self._match("STAR", "SLASH"):
            operator = self._previous
            right = self._parse_unary()
            expr = BinaryOp(expr, str(operator.value), right)
        return expr

    def _parse_unary(self) -> Expr:
        if self._match("MINUS"):
            operand = self._parse_unary()
            return UnaryOp("-", operand)
        if self._match("PLUS"):
            operand = self._parse_unary()
            return operand
        return self._parse_primary()

    def _parse_primary(self) -> Expr:
        if self._match("NUMBER"):
            token = self._previous
            return Number(float(token.value))
        if self._match("IDENT"):
            identifier_token = self._previous
            if self._match("LPAREN"):
                args = self._parse_call_arguments()
                return CallExpr(str(identifier_token.value), args)
            return Identifier(str(identifier_token.value))
        if self._match("LPAREN"):
            expr = self._parse_expr()
            self._consume("RPAREN", "Expected ')' after expression")
            return expr
        token = self._peek()
        self._error(token, "Unexpected token in expression")
        raise AssertionError("unreachable")

    def _parse_call_arguments(self) -> Tuple[Expr, ...]:
        args: List[Expr] = []
        if not self._check("RPAREN"):
            while True:
                args.append(self._parse_expr())
                if not self._match("COMMA"):
                    break
        self._consume("RPAREN", "Expected ')' after function arguments")
        return tuple(args)

    def _match(self, *types: str) -> bool:
        for token_type in types:
            if self._check(token_type):
                self._advance()
                return True
        return False

    def _consume(self, token_type: str, message: str) -> Token:
        if self._check(token_type):
            return self._advance()
        token = self._peek()
        self._error(token, message)
        raise AssertionError("unreachable")

    def _check(self, token_type: str) -> bool:
        return self._peek().type == token_type

    def _advance(self) -> Token:
        token = self._peek()
        if self._position < len(self._tokens):
            self._position += 1
        return token

    def _is_at_end(self) -> bool:
        return self._peek().type == "EOF"

    def _peek(self) -> Token:
        if self._position >= len(self._tokens):
            return self._tokens[-1]
        return self._tokens[self._position]

    @property
    def _previous(self) -> Token:
        return self._tokens[self._position - 1]

    def _error(self, token: Token, message: str) -> None:
        raise DSLParseError(message, token.line, token.column)


def parse_rules(source: str) -> List[RuleNode]:
    """Parse a string containing one or more rule definitions."""

    tokens = Tokenizer(source).tokenize()
    parser = Parser(tokens)
    return parser.parse_rules()


def parse_rule(source: str) -> RuleNode:
    """Parse a single rule definition from *source*."""

    rules = parse_rules(source)
    if len(rules) != 1:
        first = rules[0].name if rules else "<none>"
        raise DSLParseError(f"Expected exactly one rule, found {len(rules)} (first: {first})", 1, 1)
    return rules[0]
