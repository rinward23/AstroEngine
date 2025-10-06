# >>> AUTO-GEN BEGIN: pipeline-provision v1.0
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from ..detectors.common import _ensure_swiss

PROVISION_HOME = Path.home() / ".astroengine"
PROVISION_META = PROVISION_HOME / "provision.json"


def get_ephemeris_meta() -> dict[str, Any]:
    ok = _ensure_swiss()
    meta: dict[str, Any] = {"ok": bool(ok)}
    if not ok:
        return meta
from astroengine.ephemeris.swe import swe

    meta.update(
        {
            "swe_version": getattr(swe, "version", lambda: "unknown")(),
            "ephe_path": getattr(swe, "get_ephe_path", lambda: None)(),
        }
    )
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
