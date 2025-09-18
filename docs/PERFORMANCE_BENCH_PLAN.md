<!-- >>> AUTO-GEN BEGIN: Performance Bench v1.0 (instructions) -->
Targets (example):
- 30-day scan, Sun–Pluto + Nodes + Chiron, 1h step: < 250 ms on laptop with cached ephemeris.
- Refinement iterations: median ≤ 6 per exact.

Bench harness:
- Fixed seeds; pinned ephemeris; report wall-time, CPU, allocations.
- CI threshold: warn at +20%, fail at +35% regression.
<!-- >>> AUTO-GEN END: Performance Bench v1.0 (instructions) -->
