# >>> AUTO-GEN BEGIN: AE Declination Utils v1.0
from __future__ import annotations
import math

try:
    from astropy.coordinates import SkyCoord
    from astropy.coordinates import GeocentricTrueEcliptic
    import astropy.units as u
except Exception:  # pragma: no cover
    SkyCoord = None  # type: ignore
    GeocentricTrueEcliptic = None  # type: ignore
    u = None  # type: ignore


OBLIQUITY_DEG = 23.43656  # IAU 2006 mean obliquity (approx); overridable if needed


def ecl_to_dec(lon_deg: float, lat_deg: float = 0.0, ob_deg: float = OBLIQUITY_DEG) -> float:
    """Return declination (deg) from ecliptic lon/lat.
    Uses Astropy if available; otherwise applies spherical transform.
    """
    if SkyCoord is not None and GeocentricTrueEcliptic is not None and u is not None:
        c = SkyCoord(lon_deg * u.deg, lat_deg * u.deg, frame=GeocentricTrueEcliptic())
        eq = c.transform_to("gcrs")
        return float(eq.dec.deg)
    # Fallback: spherical relation
    lon = math.radians(lon_deg)
    lat = math.radians(lat_deg)
    ob = math.radians(ob_deg)
    s = math.sin(lat) * math.cos(ob) + math.cos(lat) * math.sin(ob) * math.sin(lon)
    return math.degrees(math.asin(max(-1.0, min(1.0, s))))


def antiscia_lon(lon_deg: float) -> float:
    """Antiscia (equal declination, same sign) mirror across solstitial axis.
    Formula: λ' = (180° - λ) mod 360.
    """
    return (180.0 - lon_deg) % 360.0


def contra_antiscia_lon(lon_deg: float) -> float:
    """Contra-antiscia (equal |declination|, opposite sign) mirror across equinoctial axis.
    Formula: λ'' = (-λ) mod 360 = (360° - λ) mod 360.
    """
    return (-lon_deg) % 360.0


def is_parallel(dec1_deg: float, dec2_deg: float, tol_deg: float = 0.5) -> bool:
    """Declination parallel: |dec1 - dec2| ≤ tol."""
    return abs(dec1_deg - dec2_deg) <= tol_deg


def is_contraparallel(dec1_deg: float, dec2_deg: float, tol_deg: float = 0.5) -> bool:
    """Contraparallel: |dec1 + dec2| ≤ tol (opposite signs within tolerance)."""
    return abs(dec1_deg + dec2_deg) <= tol_deg
# >>> AUTO-GEN END: AE Declination Utils v1.0
