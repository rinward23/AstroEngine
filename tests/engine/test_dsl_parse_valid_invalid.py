from __future__ import annotations

import pytest

from astroengine.engine.rules import (
    BinaryOp,
    BooleanBinaryOp,
    BooleanNot,
    CallExpr,
    DSLParseError,
    Number,
    parse_rule,
    parse_rules,
)


def test_parse_basic_rule_structure() -> None:
    source = """
    rule sunrise {
        when: not voc() and aspect(sun, moon, 3),
        then: aspect(sun, moon, 3) * 0.5,
        weight: 1.25,
        tags: ["demo", visibility]
    }
    """

    rule = parse_rule(source)

    assert rule.name == "sunrise"
    assert isinstance(rule.when, BooleanBinaryOp)
    assert rule.when.op == "and"
    assert isinstance(rule.when.left, BooleanNot)
    assert isinstance(rule.when.left.operand, CallExpr)
    assert rule.when.left.operand.name == "voc"
    assert isinstance(rule.when.right, CallExpr)
    assert rule.when.right.name == "aspect"
    assert rule.tags == ("demo", "visibility")
    assert rule.weight == pytest.approx(1.25)
    assert isinstance(rule.then, BinaryOp)
    assert isinstance(rule.then.left, CallExpr)
    assert isinstance(rule.then.right, Number)
    assert rule.then.right.value == pytest.approx(0.5)


def test_boolean_precedence_is_correct() -> None:
    source = """
    rule precedence {
        when: trigger_a() or trigger_b() and not trigger_c(),
        then: 1,
        weight: 2
    }
    """

    rule = parse_rule(source)

    assert isinstance(rule.when, BooleanBinaryOp)
    assert rule.when.op == "or"
    assert isinstance(rule.when.left, CallExpr)
    assert rule.when.left.name == "trigger_a"

    right = rule.when.right
    assert isinstance(right, BooleanBinaryOp)
    assert right.op == "and"
    assert isinstance(right.left, CallExpr)
    assert right.left.name == "trigger_b"
    assert isinstance(right.right, BooleanNot)
    assert isinstance(right.right.operand, CallExpr)
    assert right.right.operand.name == "trigger_c"


def test_invalid_boolean_expression_raises() -> None:
    source = """
    rule bad {
        when: 1 + 2,
        then: 0,
        weight: 1
    }
    """

    with pytest.raises(DSLParseError):
        parse_rule(source)


def test_parse_multiple_rules() -> None:
    source = """
    rule first {
        when: always(),
        then: 1,
        weight: 1
    }

    rule second {
        when: always(),
        then: 2,
        weight: 0.5,
        tags: [core]
    }
    """

    rules = parse_rules(source)
    assert [rule.name for rule in rules] == ["first", "second"]
    assert rules[1].tags == ("core",)
