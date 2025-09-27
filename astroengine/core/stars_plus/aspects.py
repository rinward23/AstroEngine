from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional

from astroengine.core.aspects_plus.harmonics import BASE_ASPECTS
from astroengine.core.aspects_plus.matcher import angular_sep_deg
from astroengine.core.aspects_plus.orb_policy import orb_limit

from .catalog import Star
from .geometry import mean_obliquity_deg, radec_to_ecliptic_lon_deg


def star_longitudes(ts: datetime, stars: Dict[str, Star]) -> Dict[str, float]:
    eps = mean_obliquity_deg(ts.astimezone(timezone.utc))
    out: Dict[str, float] = {}
    for name, s in stars.items():
        out[name] = radec_to_ecliptic_lon_deg(s.ra_deg, s.dec_deg, eps)
    return out


def find_star_aspects(
    ts: datetime,
    planet_lons: Dict[str, float],
    stars: Dict[str, Star],
    aspects: Iterable[str],
    policy: Dict,
    mag_max: float = 2.5,
    orb_per_star: Optional[Dict[str, float]] = None,
) -> List[Dict]:
    """Return star–planet hits at time ts.

    `orb_per_star` overrides the policy orb limit per star (conjunction family, etc.).
    """
    star_lons = star_longitudes(ts, stars)
    hits: List[Dict] = []
    for sname, slon in star_lons.items():
        s = stars[sname]
        if s.vmag > mag_max:
            continue
        for bname, blon in planet_lons.items():
            delta = angular_sep_deg(slon, blon)
            best = None
            for asp in aspects:
                ang = BASE_ASPECTS.get(asp.lower())
                if ang is None:
                    continue
                orb = abs(delta - float(ang))
                # Prefer explicit star orb override, else fallback to policy
                if orb_per_star and sname in orb_per_star:
                    limit = float(orb_per_star[sname])
                else:
                    limit = orb_limit(sname, bname, asp.lower(), policy)
                if orb <= limit + 1e-9:
                    cand = {"star": sname, "vmag": s.vmag, "planet": bname, "aspect": asp.lower(), "angle": float(ang), "delta": float(delta), "orb": float(orb), "limit": float(limit)}
                    if best is None or cand["orb"] < best["orb"]:
                        best = cand
            if best:
                hits.append(best)
    hits.sort(key=lambda h: (h["orb"], h["star"], h["planet"]))
    return hits
