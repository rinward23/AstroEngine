"""Arabic Lots engine with DSL compilation, evaluation, and event scanning."""

from .builtins import (
    LotsProfile,
    builtin_profile,
    list_builtin_profiles,
    load_custom_profiles,
    save_custom_profile,
)
from .dsl import (
    Add,
    Arc,
    Expr,
    IfDay,
    LotDef,
    LotProgram,
    Number,
    Ref,
    Sub,
    Wrap,
    compile_program,
    detect_cycles,
    parse_lot_defs,
)
from .eval import ChartContext, ChartLocation, evaluate
from .aspects import AspectHit, aspects_to_lots
from .events import LotEvent, scan_lot_events
from .sect import is_day

__all__ = [
    "Add",
    "Arc",
    "AspectHit",
    "ChartContext",
    "ChartLocation",
    "Expr",
    "IfDay",
    "LotDef",
    "LotEvent",
    "LotProgram",
    "LotsProfile",
    "Number",
    "Ref",
    "Sub",
    "Wrap",
    "aspects_to_lots",
    "builtin_profile",
    "compile_program",
    "detect_cycles",
    "evaluate",
    "is_day",
    "load_custom_profiles",
    "list_builtin_profiles",
    "parse_lot_defs",
    "save_custom_profile",
    "scan_lot_events",
]
