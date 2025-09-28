# Saturn Binding vs Growth Pack

## Overview

`saturn-binding-growth` differentiates hard aspect Saturn glue from smoother
supportive contacts. The pack introduces synergy rules for multiple Saturn hits
and overlays for composite/davison charts.

## Tags

| Sub-tag | Bucket |
| --- | --- |
| commitment | stability |
| endurance | stability |
| mastery | growth |
| resilience | stability |
| nurture | chemistry |
| discipline | stability |
| stewardship | growth |

## Profiles

| Profile | Notes |
| --- | --- |
| `default` | Balanced weighting across chemistry, stability, growth, friction. |
| `stability_plus` | Prioritises long-term anchoring themes. |
| `growth_plus` | Elevates Saturn-as-mentor dynamics. |

## Quick Start

```python
from core.interpret_plus.engine import interpret, load_rules

pack = load_rules("interpret-packs/packs/saturn-binding-growth.yaml")
request = {
    "scope": "synastry",
    "profile": "stability_plus",
    "hits": [
        {"a": "Saturn", "b": "Venus", "aspect": "square", "severity": 0.6},
        {"a": "Saturn", "b": "Sun", "aspect": "trine", "severity": 0.58},
    ],
}
findings = interpret(request, pack)
```
