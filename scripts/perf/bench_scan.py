# >>> AUTO-GEN BEGIN: bench scan v1.0
#!/usr/bin/env python
"""Quick performance benchmark for the fast transit scanner.

The script prefers the in-repo ``astroengine`` implementation but can fall
back to the auto-generated engine when the full package cannot be imported
(for example, in a minimal perf environment).
"""
from __future__ import annotations

import datetime as dt
import importlib
import importlib.util
import os
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _load_generated_fallback() -> tuple[Callable[..., object], type]:
    """Load the generated fallback engine without triggering the shim."""

    package_root = REPO_ROOT / "generated" / "astroengine"
    if not package_root.exists():  # pragma: no cover - defensive
        raise ImportError("generated fallback package missing")

    spec = importlib.util.spec_from_file_location(
        "generated_fallback",
        package_root / "__init__.py",
        submodule_search_locations=[str(package_root)],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("generated_fallback", module)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    engine = importlib.import_module("generated_fallback.engine")
    return engine.fast_scan, engine.ScanConfig


if os.getenv("ASTROENGINE_FORCE_GENERATED") == "1":
    fast_scan, ScanConfig = _load_generated_fallback()
else:
    try:
        from astroengine.engine import ScanConfig, fast_scan  # type: ignore
    except Exception:
        fast_scan, ScanConfig = _load_generated_fallback()


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
        if isinstance(h, Mapping):
            ts = h.get("timestamp")
            delta = h.get("delta")
        elif isinstance(h, Sequence) and len(h) >= 2:
            ts, delta = h[0], h[1]
        else:
            ts, delta = h, None
        ts_text = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
        print("hit:", ts_text, "Δ≈", delta)
    if dt_sec > 30.0:
        print("NOTE: >30s; consider lowering tick_minutes or limiting bodies")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
# >>> AUTO-GEN END: bench scan v1.0
