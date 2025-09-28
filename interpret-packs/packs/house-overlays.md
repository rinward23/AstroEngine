# House Overlays Pack

## Overview

`house-overlays` highlights composite and Davison placements in angular and
relationship houses. Rules emphasise Venus, Mars, luminaries, and nodal hits on
Asc/MC.

## Tags

| Sub-tag | Bucket |
| --- | --- |
| libido | chemistry |
| partnership | stability |
| destiny | growth |
| public_path | growth |
| hearth | stability |
| magnetism | chemistry |
| momentum | growth |
| nurture | chemistry |

## Profiles

| Profile | Notes |
| --- | --- |
| `default` | Balanced overlay scoring. |
| `chemistry_plus` | Elevates Venus/Mars overlays. |
| `stability_plus` | Rewards home-building and devotion placements. |

## Quick Start

```python
pack = load_rules("interpret-packs/packs/house-overlays.yaml")
req = {
    "scope": "composite",
    "positions": {"Venus": 223.0},
    "houses": {"Venus": "VII", "Mars": {"house": "I", "longitude": 15.0}},
    "angles": {"Asc": 12.0, "MC": 280.0},
}
findings = interpret(req, pack)
```
