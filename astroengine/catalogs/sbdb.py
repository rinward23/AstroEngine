# >>> AUTO-GEN BEGIN: AE SBDB Catalog v1.0
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from ..infrastructure.paths import datasets_dir

LOG = logging.getLogger(__name__)

CACHE_DIR = datasets_dir() / "sbdb_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

try:
    from astroquery.jplsbdb import SBDB
except Exception as exc:  # pragma: no cover
    LOG.warning("astroquery.jplsbdb unavailable: %s", exc)
    SBDB = None  # type: ignore


@dataclass
class SBDBObject:
    designation: str
    data: dict[str, Any]


def fetch_sbdb(designation: str, use_cache: bool = True) -> SBDBObject:
    """Fetch SBDB JSON for a small body by designation/number.
    If offline or astroquery missing, will load from cache if available.
    """
    key = designation.replace(" ", "_")
    fpath = CACHE_DIR / f"{key}.json"

    if SBDB is not None:
        try:
            res = SBDB.query(designation, closest=True)
            if isinstance(res, dict):
                if use_cache:
                    fpath.write_text(json.dumps(res, indent=2))
                return SBDBObject(designation=designation, data=res)
        except Exception as exc:  # pragma: no cover - network/cache fallback
            LOG.warning("SBDB query failed for %s, falling back to cache: %s", designation, exc)

    if use_cache and fpath.exists():
        return SBDBObject(designation=designation, data=json.loads(fpath.read_text()))

    raise RuntimeError("SBDB query failed and no cache available")


# >>> AUTO-GEN END: AE SBDB Catalog v1.0
