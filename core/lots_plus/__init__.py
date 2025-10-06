"""Arabic Lots engine and catalog utilities."""

from .catalog import (
    BUILTIN,
    REGISTRY,
    LotDef,
    Sect,
    compute_lot,
    compute_lots,
    register_lot,
    unregister_lot,
)
from .engine import deg_add, deg_sub, eval_formula, norm360
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
