"""Arabic Lots engine and catalog utilities."""

from .engine import eval_formula, norm360, deg_add, deg_sub
from .catalog import (
    LotDef,
    Sect,
    BUILTIN,
    REGISTRY,
    compute_lot,
    compute_lots,
    register_lot,
    unregister_lot,
)
from .parser import (
    FormulaSyntaxError,
    extract_symbols,
    parse_formula,
    validate_formula,
)

__all__ = [
    "eval_formula",
    "norm360",
    "deg_add",
    "deg_sub",
    "FormulaSyntaxError",
    "LotDef",
    "Sect",
    "BUILTIN",
    "REGISTRY",
    "compute_lot",
    "compute_lots",
    "register_lot",
    "unregister_lot",
    "extract_symbols",
    "parse_formula",
    "validate_formula",
]
