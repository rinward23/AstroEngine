from __future__ import annotations
import math
from datetime import datetime, timedelta, timezone
from typing import Dict

# --------------------------- Angles & time ---------------------------------

def norm360(x: float) -> float:
    v = x % 360.0
    return v + 360.0 if v < 0 else v


def mean_obliquity_deg(ts: datetime) -> float:
    # IAU 2006 approximation; good to <0.01° over modern times
    # Source numeric: ε = 23°26′21.448″ − 46.8150″T − 0.00059″T^2 + 0.001813″T^3, T centuries from J2000
    # We implement in degrees.
    J2000 = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)
    T = (ts - J2000).total_seconds() / (36525.0 * 86400.0)
    arcsec = 21.448 - 46.8150*T - 0.00059*(T**2) + 0.001813*(T**3)
    deg = 23 + 26/60 + arcsec/3600.0
    return deg


# --------------------------- Coord transforms ------------------------------

def radec_to_ecliptic_lon_deg(ra_deg: float, dec_deg: float, epsilon_deg: float) -> float:
    ra = math.radians(ra_deg)
    dec = math.radians(dec_deg)
    eps = math.radians(epsilon_deg)
    # tan λ = (sin α cos ε + tan δ sin ε) / cos α
    num = math.sin(ra)*math.cos(eps) + math.tan(dec)*math.sin(eps)
    den = math.cos(ra)
    lam = math.degrees(math.atan2(num, den))
    return norm360(lam)


# --------------------------- Sidereal time ---------------------------------

def gmst_deg(ts: datetime) -> float:
    # Vallado-ish approximation for GMST in degrees
    # Convert to Julian Date
    def jd(dt: datetime) -> float:
        y = dt.year; m = dt.month; d = dt.day
        hr = dt.hour + dt.minute/60 + dt.second/3600 + dt.microsecond/3.6e9
        if m <= 2:
            y -= 1; m += 12
        A = int(y/100); B = 2 - A + int(A/4)
        JD = int(365.25*(y+4716)) + int(30.6001*(m+1)) + d + B - 1524.5 + hr/24.0
        return JD
    JD = jd(ts)
    D = JD - 2451545.0
    T = D / 36525.0
    GMST = 280.46061837 + 360.98564736629*D + 0.000387933*T*T - (T*T*T)/38710000.0
    return norm360(GMST)


def lst_deg(ts: datetime, lon_deg_east: float) -> float:
    return norm360(gmst_deg(ts) + lon_deg_east)


# --------------------------- Rise/Set/Culmination --------------------------

def rise_set_hour_angle_deg(phi_deg: float, dec_deg: float) -> float | None:
    # cos H0 = -tan φ tan δ ; if |cosH0|>1: never rises/sets
    phi = math.radians(phi_deg)
    dec = math.radians(dec_deg)
    cosH0 = -math.tan(phi) * math.tan(dec)
    if abs(cosH0) > 1.0:
        return None
    H0 = math.degrees(math.acos(cosH0))
    return H0  # in degrees; rising at -H0, setting at +H0


def event_lst_deg(ra_deg: float, H_deg: float) -> float:
    # LST = α + H (deg)
    return norm360(ra_deg + H_deg)


def refine_event_time(ts_guess: datetime, lon_east: float, target_lst_deg: float, max_iter: int = 6) -> datetime:
    # Simple fixed-point iteration: LST(ts) ≈ target
    ts = ts_guess
    for _ in range(max_iter):
        cur = lst_deg(ts, lon_east)
        # convert difference (deg) to seconds using dLST/dt ≈ 360.9856°/sidereal day
        delta_deg = (target_lst_deg - cur + 540) % 360 - 180
        sec = delta_deg / 360.98564736629 * 86164.0905
        ts = ts + timedelta(seconds=sec)
    return ts


def approximate_transit_times(date_utc: datetime, lon_east: float, ra_deg: float, dec_deg: float, phi_deg: float) -> Dict[str, datetime | None]:
    # date_utc at 0h is reference. Compute LST0, then get LST targets for rise/set (if possible) and transit.
    base = date_utc.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    H0 = rise_set_hour_angle_deg(phi_deg, dec_deg)
    out: Dict[str, datetime | None] = {"rise": None, "set": None, "culminate": None}
    # Culmination (upper transit): H=0 → LST=α
    L_culm = event_lst_deg(ra_deg, 0.0)
    guess = base + timedelta(hours=12)  # rough
    out["culminate"] = refine_event_time(guess, lon_east, L_culm)
    if H0 is not None:
        # Rising: H = -H0 ; Setting: H = +H0
        L_rise = event_lst_deg(ra_deg, -H0)
        L_set = event_lst_deg(ra_deg, +H0)
        out["rise"] = refine_event_time(base + timedelta(hours=6), lon_east, L_rise)
        out["set"] = refine_event_time(base + timedelta(hours=18), lon_east, L_set)
    return out
