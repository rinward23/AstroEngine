<!-- >>> AUTO-GEN BEGIN: Project Guide v1.0 -->
# AstroEngine — Project Guide

## Purpose
Authoritative transit computation and astrology tooling with stable APIs, predictable math, and concise outputs.

## Components
- **Ephemeris Provider**: skyfield/swe backends behind a common interface.
- **Detectors**: ecliptic aspects (core), declination, antiscia, (later) midpoints/ingresses.
- **Refinement**: secant/bisection to exactness.
- **Scoring**: severity profiles and partile boosts.
- **Export**: SQLite/Parquet.

## Conventions
- UTC for all timestamps; internal ephemeris time in TT.
- Angles normalized to [0,360), Δλ tracked continuously.
- Orbs by body + aspect family; partile at 0°10′ unless profile overrides.

## Change Packets (Chat-Only)
Use the `AUTO-GEN` markers and `# ENSURE-LINE` hints. Replace blocks with the same name; otherwise append.

## Roadmap
R1: Transit MVP → R2: declination+antiscia+DSL → R3: ingresses/lunations/stations.
<!-- >>> AUTO-GEN END: Project Guide v1.0 -->
