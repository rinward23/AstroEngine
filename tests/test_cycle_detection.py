import pytest

from astroengine.engine.lots import compile_program, detect_cycles, parse_lot_defs


def test_detects_simple_cycle():
    program = parse_lot_defs("A = B\nB = A")
    cycles = detect_cycles(program)
    assert cycles, "cycle should be detected"


def test_compile_raises_on_cycle():
    program = parse_lot_defs("A = B\nB = A")
    with pytest.raises(ValueError):
        compile_program(program)


def test_compile_resolves_acyclic():
    program = parse_lot_defs("A = B\nB = Sun")
    compiled = compile_program(program)
    assert list(compiled.order) == ["B", "A"]
