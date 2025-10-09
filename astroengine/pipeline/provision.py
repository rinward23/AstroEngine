# >>> AUTO-GEN BEGIN: pipeline-provision v1.0
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

from ..detectors.common import _ensure_swiss
from ..engine.ephe_runtime import init_ephe
from ..ephemeris.swe import swe
from ..config.settings import load_settings

PROVISION_HOME = Path.home() / ".astroengine"
PROVISION_META = PROVISION_HOME / "provision.json"


def get_ephemeris_meta() -> dict[str, Any]:
    """
    Probe Swiss Ephemeris availability and capability at the configured year caps.
    Returns a JSON-serializable dict for UI/doctor pages and provisioning storage.
    """
    installed = False
    min_ok = False
    max_ok = False
    error: str | None = None
    ephe_path: str | None = None

    try:
        _ensure_swiss()
        _ = swe()  # lazy import
        base_flag = init_ephe()
        installed = True
        s = load_settings()
        # Try to detect current ephemeris path if set
        try:
            # If your utils expose a getter, use it; else rely on swe.get_library_path()
            ephe_path = getattr(swe(), "get_library_path", lambda: None)() or None
        except Exception:
            ephe_path = None

        def _can(year: int) -> bool:
            try:
                jd = swe().julday(year, 1, 1, 12.0)
                pos = swe().calc_ut(jd, swe().SUN, base_flag)[0]
                return all(not math.isnan(x) for x in pos)
            except Exception:
                return False

        min_ok = _can(s.swiss_caps.min_year)
        max_ok = _can(s.swiss_caps.max_year)

    except Exception as e:
        error = str(e)

    meta = {
        "installed": installed,
        "ephemeris_path": ephe_path,
        "min_year_ok": bool(min_ok),
        "max_year_ok": bool(max_ok),
        "error": error,
        "ts": int(time.time()),
    }
    return meta


def provision_ephemeris() -> dict[str, Any]:
    meta = get_ephemeris_meta()
    PROVISION_HOME.mkdir(parents=True, exist_ok=True)
    meta["provisioned_at"] = int(time.time())
    with open(PROVISION_META, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    return meta


def is_provisioned() -> bool:
    return PROVISION_META.is_file()
# >>> AUTO-GEN END: pipeline-provision v1.0
