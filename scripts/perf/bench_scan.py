# >>> AUTO-GEN BEGIN: bench scan v1.0
#!/usr/bin/env python
"""
Quick performance benchmark:
- scans Sun→natal Venus conj over N days at tick=60m
- prints hits and wall time
Run: python scripts/perf/bench_scan.py
"""
import datetime as dt
import os
import time

from generated.astroengine.engine import ScanConfig, fast_scan  # fallback

try:
    from astroengine.engine import ScanConfig as _SC
    from astroengine.engine import fast_scan as _fs  # type: ignore

    fast_scan, ScanConfig = _fs, _SC
except Exception:
    pass


def main():
    if not os.getenv("SE_EPHE_PATH"):
        print("WARN: SE_EPHE_PATH not set; Swiss may fail.")
    start = dt.datetime(2025, 1, 1, 0, 0)
    end = dt.datetime(2025, 1, 31, 0, 0)
    cfg = ScanConfig(
        body=1, natal_lon_deg=195.0, aspect_angle_deg=0.0, orb_deg=6.0, tick_minutes=60
    )
    t0 = time.time()
    try:
        hits = fast_scan(start, end, cfg)
    except Exception as e:
        print("ERROR:", e)
        return 2
    dt_sec = time.time() - t0
    print(
        f"fast_scan: days={(end-start).days}, ticks={(end-start).days*24}, "
        f"hits={len(hits)}, wall={dt_sec:.2f}s"
    )
    for h in hits[:3]:
        print("hit:", h[0].isoformat(), "Δ≈", h[1])
    if dt_sec > 30.0:
        print("NOTE: >30s; consider lowering tick_minutes or limiting bodies")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
# >>> AUTO-GEN END: bench scan v1.0
