
<!-- >>> AUTO-GEN BEGIN: Project Instructions v1.0 -->
# AstroEngine — Project Instructions

## Mission
Build a modular, testable engine to compute astrological transits (MVP) and, over time, broader techniques (declination, antiscia, midpoints, harmonics, ingresses, lunations, returns, etc.). Accuracy, reproducibility, and clean APIs are non-negotiable.

## Roles & Workflow (Chat-Only)
- You: prioritize features and approve defaults (house system, orbs, profiles).
- Assistant: deliver deterministic **Change Packets (CPs)** with `AUTO-GEN` blocks and `# ENSURE-LINE` hints.
- Apply rule: if a same-name block exists, replace that region; otherwise append. Re-pasting is safe.

## Scope (MVP)
- Bodies: Sun–Pluto, Mean/True Nodes; Chiron (opt).
- Points: ASC/MC/IC/DSC; Lots (Fortune/Spirit, later).
- Aspects: 0/60/90/120/180 (core); optional 30/45/135/150; declination parallels/contra; antiscia.
- Time: I/O in ISO-8601 UTC; ephemeris eval in TT.
- Angles: normalize to [0°, 360°); track Δλ continuously across 0°/360°.
- Orbs (defaults): luminaries 8°, personal 6°, social 5°, outer 4°, minors 2°; declination 0°30′; partile ≤ 0°10′.

## Public API (stable imports)
`TransitEngine`, `TransitScanConfig`, `TransitEvent` in `astroengine.transit.api`.

## Quality Bar
Deterministic results; documented units; retrograde guards; tests (unit + acceptance); CI for ruff/black/mypy/pytest.

## Roadmap
R1: Transit API + detectors + refinement + schema CI →  
R2: declination + antiscia + severity/orb profiles + CLI →  
R3: ingresses/lunations/stations calendar + exporters.
<!-- >>> AUTO-GEN END: Project Instructions v1.0 -->

