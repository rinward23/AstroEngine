# >>> AUTO-GEN BEGIN: docs-algorithms v1.0
## Lunations
Root-finding on Moon–Sun elongation equals {0°, 90°, 180°, 270°}. Bracket with 0.5d, secant→bisection refinement.

## Eclipses
Filter lunations to New/Full where |Moon ecliptic latitude| ≤ 1.6°. This flags probable solar/lunar eclipses.

## Planetary Stations
Zero-crossing of central-difference longitudinal rate (wrap-aware). Refine root to ~1e-6°.

## Secondary Progressions
Map real anniversary y to ephemeris at natal + y **days**. Sample annually; events contain method/body/ts.

## Solar-Arc Directions
Arc = progressed Sun longitude (natal+y days) − natal Sun longitude. Sample annually for all bodies; events carry method/body/ts.
# >>> AUTO-GEN END: docs-algorithms v1.0
