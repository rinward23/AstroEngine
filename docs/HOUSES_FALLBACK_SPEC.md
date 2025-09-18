<!-- >>> AUTO-GEN BEGIN: House Fallbacks v1.0 (instructions) -->
Rules:
- When quadrant system fails (e.g., Placidus near poles), fall back to Whole Sign with a warning flag.
- Record chosen fallback in outputs.
QA:
- Tests with latitudes > 66° verify graceful fallback, not crash.
<!-- >>> AUTO-GEN END: House Fallbacks v1.0 (instructions) -->
