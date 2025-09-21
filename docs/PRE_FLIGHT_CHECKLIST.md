# >>> AUTO-GEN BEGIN: pre-flight checklist v1.0
# AstroEngine — Pre-Flight Checklist (v0.1)

## Environment
- [ ] Python pinned to **3.11** in CI (Actions).
- [ ] `pyswisseph==2.10.3.2` installed where Swiss is needed.
- [ ] `SE_EPHE_PATH` points to valid Swiss ephemeris folder.

## Functional smoke
- [ ] `python -c "import swisseph as swe; print(swe.__version__)"` works.
- [ ] `scripts/swe_smoketest.py` prints a Julian Day and does not error.

## Performance
- [ ] `pytest -q -m perf` passes locally.
- [ ] `python scripts/perf/bench_scan.py` completes in a reasonable time window.

## Data & Registry
- [ ] `registry/aspects.yaml` has core aspects (0/60/90/120/180).
- [ ] `registry/orbs_policy.yaml` has `orbs_default` with luminaries/personal/social/outer/minors.

## Safety nets
- [ ] AUTO-GEN fence validators green.
- [ ] Issue triage workflow updated meta health report.
# >>> AUTO-GEN END: pre-flight checklist v1.0
