# Luminary Emphasis Pack

## Overview

`luminary-emphasis` packages Sun/Moon resonance, double whammy detections, and
nodal overlays for composite and Davison charts.

## Tags

| Sub-tag | Bucket |
| --- | --- |
| nurture | chemistry |
| heart_sync | chemistry |
| resonance | stability |
| radiance | growth |
| cadence | stability |
| destiny | growth |
| roots | stability |
| harmony | stability |

## Profiles

| Profile | Notes |
| --- | --- |
| `default` | Baseline weighting. |
| `chemistry_plus` | Accentuates heart-spark signatures. |
| `stability_plus` | Favors long-term lunar cadence cues. |

## Quick Start

```python
pack = load_rules("interpret-packs/packs/luminary-emphasis.yaml")
req = {
    "scope": "synastry",
    "profile": "chemistry_plus",
    "hits": [
        {"a": "Sun", "b": "Moon", "aspect": "trine", "severity": 0.6},
        {"a": "Moon", "b": "Sun", "aspect": "sextile", "severity": 0.52},
    ],
}
findings = interpret(req, pack)
```
