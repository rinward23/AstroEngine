# >>> AUTO-GEN BEGIN: pre-flight checklist v1.0
# AstroEngine — Pre-Flight Checklist (v0.1)

## Environment
- [x] Python pinned to **3.11** in CI (Actions) (`.github/workflows/ci.yml`).
- [x] `pyswisseph==2.10.3.2` installed where Swiss is needed (`python -m astroengine.infrastructure.environment …`).
- [x] `SE_EPHE_PATH` points to valid Swiss ephemeris folder (`datasets/swisseph_stub` for CI, replace with production pack before release).

## Functional smoke
- [x] `python -c "import swisseph as swe; print(swe.__version__)"` works.
- [x] `scripts/swe_smoketest.py` prints a Julian Day and does not error.

## Performance
- [x] `pytest -q -m perf` passes locally.
- [x] `python scripts/perf/bench_scan.py` completes in a reasonable time window.

## Data & Registry
- [x] `registry/aspects.yaml` has core aspects (0/60/90/120/180).
- [x] `registry/orbs_policy.yaml` has `orbs_default` with luminaries/personal/social/outer/minors.

## Safety nets
- [ ] AUTO-GEN fence validators green.
- [ ] Issue triage workflow updated meta health report.
# >>> AUTO-GEN END: pre-flight checklist v1.0
