#!/usr/bin/env python
import argparse
import datetime as dt
import swisseph as swe

def jd_from_iso(s: str) -> float:
    # accept ...Z or ...+00:00; coerce to aware UTC
    s = s.replace("Z", "+00:00")
    t = dt.datetime.fromisoformat(s)
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.timezone.utc)
    else:
        t = t.astimezone(dt.timezone.utc)
    hour = t.hour + t.minute/60 + t.second/3600 + t.microsecond/3.6e9
    return swe.julday(t.year, t.month, t.day, hour)

def calc_lon_deg(jd: float, body: int) -> float:
    """Return ecliptic longitude in degrees for body at JD (geocentric)."""
    try:
        xx, _ = swe.calc_ut(jd, body, swe.FLG_SWIEPH)
    except Exception:
        xx, _ = swe.calc_ut(jd, body, swe.FLG_MOSEPH)
    return xx[0]  # longitude (deg)

def fmt_lon(lon: float) -> str:
    signs = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
             "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
    lon %= 360.0
    s = int(lon // 30)
    d = int(lon % 30)
    m = int((lon - (s*30 + d)) * 60)
    return f"{signs[s]} {d:02d}°{m:02d}′"

def nearest_major_aspect(sep: float) -> tuple[int, float]:
    """Return (aspect_angle, orb_deg) for sep to nearest of 0,60,90,120,180."""
    majors = [0, 60, 90, 120, 180]
    # minimal circular distance: wrap to [-180,180]
    def circ_delta(a, b):
        d = (a - b + 180.0) % 360.0 - 180.0
        return abs(d)
    best = min(((circ_delta(sep, a), a) for a in majors), key=lambda x: x[0])
    return best[1], best[0]

def main():
    now_utc = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    parser = argparse.ArgumentParser()
    parser.add_argument("--utc", default=now_utc.isoformat().replace("+00:00","Z"),
                        help="UTC timestamp ISO-8601 (default: now), e.g. 2025-09-19T18:05:00Z")
    args = parser.parse_args()

    jd = jd_from_iso(args.utc)
    sun  = calc_lon_deg(jd, swe.SUN)
    moon = calc_lon_deg(jd, swe.MOON)
    sep = (moon - sun) % 360.0
    aspect, orb = nearest_major_aspect(sep)

    print("UTC:", args.utc)
    print("Sun :", fmt_lon(sun))
    print("Moon:", fmt_lon(moon))
    print(f"Sun↔Moon sep: {sep:6.2f}°  → nearest aspect {aspect}°  orb {orb:.2f}°")

if __name__ == "__main__":
    main()
