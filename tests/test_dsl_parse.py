from astroengine.engine.lots import (
    Add,
    Arc,
    IfDay,
    LotDef,
    Number,
    Ref,
    Sub,
    parse_lot_defs,
)


def test_parse_simple_expression():
    program = parse_lot_defs("Fortune = ASC + arc(Moon, Sun)")
    assert len(program.definitions) == 1
    fortune = program.definitions[0]
    assert isinstance(fortune, LotDef)
    assert fortune.name == "Fortune"
    assert isinstance(fortune.expr, Add)


def test_parse_nested_if_day():
    program = parse_lot_defs(
        "Spirit = if_day(ASC + arc(Sun, Moon), ASC + arc(Moon, Sun))"
    )
    spirit = program.definitions[0]
    assert isinstance(spirit.expr, IfDay)
    assert isinstance(spirit.expr.day_expr, Add)
    assert isinstance(spirit.expr.day_expr.right, Arc)
    assert isinstance(spirit.expr.night_expr, Add)


def test_parse_subtraction():
    program = parse_lot_defs("Lot = Moon - Sun - ASC")
    expr = program.definitions[0].expr
    assert isinstance(expr, Sub)
    assert isinstance(expr.left, Sub)
    assert isinstance(expr.right, Ref)


def test_parse_number_literal():
    program = parse_lot_defs("Test = 15.5")
    expr = program.definitions[0].expr
    assert isinstance(expr, Number)
    assert expr.value == 15.5
