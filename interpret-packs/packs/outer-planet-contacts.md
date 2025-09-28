# Outer-Planet Contacts Pack

## Overview

`outer-planet-contacts` captures Uranus freedom jolts, Neptune idealism, and
Pluto transformation. Rules include compound triggers when multiple outers touch
Venus plus saturation checks for Neptune-heavy charts.

## Tags

| Sub-tag | Bucket |
| --- | --- |
| freedom | chemistry |
| disruption | friction |
| dreams | chemistry |
| ideals | growth |
| transformation | growth |
| intensity | chemistry |
| liberation | chemistry |
| destiny | growth |

## Profiles

| Profile | Notes |
| --- | --- |
| `default` | Even weighting of all buckets. |
| `chemistry_plus` | Highlights electric/romantic signatures. |
| `growth_plus` | Emphasises visionary and evolutionary storylines. |

## Quick Start

```python
pack = load_rules("interpret-packs/packs/outer-planet-contacts.yaml")
req = {
    "scope": "synastry",
    "hits": [
        {"a": "Uranus", "b": "Venus", "aspect": "square", "severity": 0.6},
        {"a": "Neptune", "b": "Moon", "aspect": "trine", "severity": 0.58},
        {"a": "Pluto", "b": "Mars", "aspect": "conjunction", "severity": 0.62},
    ],
}
findings = interpret(req, pack)
```
