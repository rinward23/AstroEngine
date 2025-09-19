<!-- >>> AUTO-GEN BEGIN: Docker Plan v1.0 (instructions) -->
Images:
- runtime: astroengine[skyfield,parquet,cli] + cached de440s.
- lab: adds notebooks + dev extras.
Entrypoints:
- `astroengine transits scan` (future) and `ephem pull` helper.
Cache volume for ephemeris; non-root user.
<!-- >>> AUTO-GEN END: Docker Plan v1.0 (instructions) -->
