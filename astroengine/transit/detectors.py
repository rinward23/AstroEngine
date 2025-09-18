# >>> AUTO-GEN BEGIN: Detectors v1.0 (ecliptic core)
from typing import Iterable, Sequence
from .api import TransitEvent, AspectName

# Required state keys per body: lon_deg (0—360), lon_speed_deg_per_day (signed)

ASPECT_ANGLES = {
    "conjunction": 0.0,
    "sextile": 60.0,
    "square": 90.0,
    "trine": 120.0,
    "opposition": 180.0,
    "semisextile": 30.0,
    "semisquare": 45.0,
    "sesquisquare": 135.0,
    "quincunx": 150.0,
}


def norm180(x: float) -> float:
    """Map degrees to (-180, 180]."""
    x = (x + 180.0) % 360.0 - 180.0
    return x if x != -180.0 else 180.0


def detect_ecliptic_contacts(state: dict, natal: dict, aspects: Sequence[AspectName], orbs) -> Iterable[TransitEvent]:
    """
    Rough detection at a cadence tick.
    - `state`: {body: {"lon_deg": float, "lon_speed_deg_per_day": float}}
    - `natal`: {point: {"lon_deg": float}}
    - `orbs`: callable (body, point, aspect) -> orb_deg
    Yields coarse TransitEvent stubs (t_exact filled by refinement).
    """
    for body, bdat in state.items():
        lon_t = bdat.get("lon_deg")
        spd_t = bdat.get("lon_speed_deg_per_day", 0.0)
        if lon_t is None:
            continue
        for point, pdat in natal.items():
            lon_n = pdat.get("lon_deg")
            if lon_n is None:
                continue
            d = norm180(lon_t - lon_n)
            for asp in aspects:
                theta = ASPECT_ANGLES.get(asp)
                if theta is None:
                    continue
                diff = norm180(d - norm180(theta))
                orb_allow = orbs(body, point, asp)
                if abs(diff) <= orb_allow:
                    applying = spd_t < 0 if diff > 0 else spd_t > 0
                    yield TransitEvent(
                        t_exact="",  # filled later
                        t_applying=applying,
                        partile=False,
                        aspect=asp,
                        transiting_body=body,
                        natal_point=point,
                        orb_deg=abs(diff),
                        severity=0.0,
                        family=f"{body}→{point} {asp}",
                        lon_transit=lon_t,
                        lon_natal=lon_n,
                        decl_transit=None,
                        notes=None,
                    )
# >>> AUTO-GEN END: Detectors v1.0 (ecliptic core)
