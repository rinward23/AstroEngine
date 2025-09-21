# >>> AUTO-GEN BEGIN: AE Body Classes v1.0
from __future__ import annotations
from typing import Dict

CLASS_OF: Dict[str, str] = {
    "sun": "luminary",
    "moon": "luminary",
    "mercury": "personal",
    "venus": "personal",
    "mars": "personal",
    "jupiter": "social",
    "saturn": "social",
    "uranus": "outer",
    "neptune": "outer",
    "pluto": "outer",
}


def body_class(name: str) -> str:
    return CLASS_OF.get(name.lower(), "outer")
# >>> AUTO-GEN END: AE Body Classes v1.0
