# >>> AUTO-GEN BEGIN: pipeline-provision v1.0
from __future__ import annotations
from typing import Dict, Any
from pathlib import Path
import json
import time

from ..detectors.common import _ensure_swiss

PROVISION_HOME = Path.home() / ".astroengine"
PROVISION_META = PROVISION_HOME / "provision.json"


def get_ephemeris_meta() -> Dict[str, Any]:
    ok = _ensure_swiss()
    meta: Dict[str, Any] = {"ok": bool(ok)}
    if not ok:
        return meta
    import swisseph as swe  # type: ignore
    meta.update({
        "swe_version": getattr(swe, "version", lambda: "unknown")(),
        "ephe_path": getattr(swe, "get_ephe_path", lambda: None)(),
    })
    return meta


def provision_ephemeris() -> Dict[str, Any]:
    meta = get_ephemeris_meta()
    PROVISION_HOME.mkdir(parents=True, exist_ok=True)
    meta["provisioned_at"] = int(time.time())
    with open(PROVISION_META, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    return meta


def is_provisioned() -> bool:
    return PROVISION_META.is_file()
# >>> AUTO-GEN END: pipeline-provision v1.0
