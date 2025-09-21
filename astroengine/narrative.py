# >>> AUTO-GEN BEGIN: narrative-skeleton v1.0
from __future__ import annotations
from typing import Dict

try:
    from jinja2 import Template
except Exception:  # pragma: no cover
    Template = None  # type: ignore

_DEFAULT = """
{{ title }}\n\n{% for e in events %}- {{ e }}\n{% endfor %}
"""

def render_simple(title: str, events: Dict) -> str:
    if Template is None:
        raise RuntimeError("Narrative extra not installed. Use: pip install -e .[narrative]")
    return Template(_DEFAULT).render(title=title, events=events)
# >>> AUTO-GEN END: narrative-skeleton v1.0
