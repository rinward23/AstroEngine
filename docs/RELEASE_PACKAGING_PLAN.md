<!-- >>> AUTO-GEN BEGIN: Release & Packaging v1.0 (instructions) -->
PyPI:
- Extras: skyfield, swe, parquet, cli, dev, maps. Wheels for Linux/macOS/Windows.
- Version sourced from git tags via setuptools-scm; fallback version is `0.0.0` so
  production wheels never publish `0+unknown` metadata.
Conda-forge:
- After 0.1.0, publish core + -skyfield variant.
Docker:
- Runtime image with cached ephemeris; lab image with notebooks.
Lockfiles:
- Pin transitive dependencies with `pip-compile` (`requirements.in → requirements.lock/py311.txt`).
  `uv pip compile` is acceptable in constrained environments as long as hashes are
  recorded.
Versioning:
- 0.0.x schemas/validation; 0.1.0 adds engine API; maintain compatibility matrix.
Build farm:
- Manylinux wheels (via cibuildwheel on GitHub Actions) required once native
  speedups land; optional otherwise.
<!-- >>> AUTO-GEN END: Release & Packaging v1.0 (instructions) -->
