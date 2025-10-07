# >>> AUTO-GEN BEGIN: AE Skyfield Fixed Stars v1.0
from __future__ import annotations

import csv
import logging

from ..infrastructure.paths import datasets_dir

LOG = logging.getLogger(__name__)

try:
    from skyfield.api import Star, load
except Exception as exc:  # pragma: no cover
    LOG.warning("Skyfield unavailable, fixed star computations disabled: %s", exc)
    Star = None
    load = None

DATASET = datasets_dir() / "star_names_iau.csv"


def _load_kernel():
    for name in ("de440s.bsp", "de421.bsp", "de430t.bsp"):
        try:
            return load(name)
        except Exception as exc:  # pragma: no cover - kernel search guard
            LOG.debug("Unable to load kernel %s: %s", name, exc)
    raise FileNotFoundError("No local JPL kernel found (e.g., de440s.bsp)")


def _lookup_ra_dec(name: str) -> tuple[float, float]:
    if not DATASET.exists():
        raise FileNotFoundError(f"Dataset not found: {DATASET}")
    n = name.strip().lower()
    with open(DATASET, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            if row["name"].strip().lower() == n:
                ra_deg = float(row["ra_deg"])  # J2000
                dec_deg = float(row["dec_deg"])  # J2000
                return ra_deg, dec_deg
    raise KeyError(f"Star not found in dataset: {name}")


def star_lonlat(name: str, iso_utc: str) -> tuple[float, float]:
    """Return ecliptic longitude/latitude (deg) true-of-date using Skyfield.

    Requires a local JPL kernel (e.g., de440s.bsp) and uses the bundled CSV to
    map star names to RA/Dec (J2000) values.
    """
    if Star is None or load is None:
        raise ImportError("skyfield/jplephem not installed")
    ra_deg, dec_deg = _lookup_ra_dec(name)
    kern = _load_kernel()
    ts = load.timescale()
    t = ts.utc(
        *map(
            int, iso_utc.replace("T", "-").replace(":", "-").rstrip("Z").split("-")[:6]
        )
    )
    earth = kern["earth"]
    s = Star(ra_hours=ra_deg / 15.0, dec_degrees=dec_deg)
    ecl = earth.at(t).observe(s).apparent().ecliptic_position()
    lon, lat, _ = ecl.spherical_latlon()
    return float(lon.degrees % 360.0), float(lat.degrees)


# >>> AUTO-GEN END: AE Skyfield Fixed Stars v1.0
