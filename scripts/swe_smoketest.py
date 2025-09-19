# >>> AUTO-GEN BEGIN: Swiss Ephemeris Smoketest v1.0
#!/usr/bin/env python
"""
Swiss Ephemeris smoketest:
- Prints positions for Sun..Pluto + Node + Chiron
- Lists major aspect hits (0/60/90/120/180) within default orbs
- Finds ephemeris via SE_EPHE_PATH or common system dirs
"""
import os
import argparse
import datetime as dt
import itertools
import swisseph as swe

SIGNS = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]

BODIES = [
    ("Sun", swe.SUN),
    ("Moon", swe.MOON),
    ("Mercury", swe.MERCURY),
    ("Venus", swe.VENUS),
    ("Mars", swe.MARS),
    ("Jupiter", swe.JUPITER),
    ("Saturn", swe.SATURN),
    ("Uranus", swe.URANUS),
    ("Neptune", swe.NEPTUNE),
    ("Pluto", swe.PLUTO),
    ("Node", swe.MEAN_NODE),  # use swe.TRUE_NODE if preferred
    ("Chiron", swe.CHIRON),
]

MAJORS = [0, 60, 90, 120, 180]

# --- ephemeris path detection ---
ephe = os.environ.get("SE_EPHE_PATH")
if not ephe:
    for p in ("/usr/share/sweph", "/usr/share/libswisseph", os.path.expanduser("~/.sweph")):
        if os.path.isdir(p):
            ephe = p
            break
if ephe:
    swe.set_ephe_path(ephe)

def jd_from_iso(s: str) -> float:
    s = s.replace("Z", "+00:00")
    t = dt.datetime.fromisoformat(s)
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.timezone.utc)
    else:
        t = t.astimezone(dt.timezone.utc)
    hour = t.hour + t.minute / 60 + t.second / 3600 + t.microsecond / 3.6e9
    return swe.julday(t.year, t.month, t.day, hour)

def calc_lon_deg(jd: float, body: int) -> float:
    try:
        xx, _ = swe.calc_ut(jd, body, swe.FLG_SWIEPH)
    except Exception:
        xx, _ = swe.calc_ut(jd, body, swe.FLG_MOSEPH)  # may not cover Node/Chiron
    return xx[0]  # longitude degrees

def fmt_lon(lon: float) -> str:
    lon %= 360.0
    s = int(lon // 30)
    d = int(lon % 30)
    m = int((lon - (s * 30 + d)) * 60)
    return f"{SIGNS[s]} {d:02d}°{m:02d}′"

def circ_delta(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)

def nearest_major_aspect(sep: float):
    best = min(((circ_delta(sep, a), a) for a in MAJORS), key=lambda x: x[0])
    return best[1], best[0]

def orb_policy(a: str, b: str, angle: int) -> float:
    def bucket(n):
        if n in ("Sun", "Moon"):
            return 8.0
        if n in ("Mercury", "Venus", "Mars"):
            return 6.0
        if n in ("Jupiter", "Saturn"):
            return 5.0
        if n in ("Uranus", "Neptune", "Pluto"):
            return 4.0
        return 3.0  # Node/Chiron

    return min(bucket(a), bucket(b))

def main():
    now_utc = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--utc",
        default=now_utc.isoformat().replace("+00:00", "Z"),
        help="UTC ISO-8601 (default: now)",
    )
    args = ap.parse_args()
    jd = jd_from_iso(args.utc)

    positions, skipped = {}, []
    for name, code in BODIES:
        try:
            positions[name] = calc_lon_deg(jd, code)
        except Exception as e:
            skipped.append((name, str(e)))

    print("UTC:", args.utc)
    for name in positions:
        print(f"{name:7s} {fmt_lon(positions[name])}")

    if skipped:
        print("\nSkipped (no ephemeris available):")
        for name, msg in skipped:
            print(f" - {name}: {msg.splitlines()[-1]}")

    print("\nMajor aspect hits (<= orb policy):")
    hits = []
    keys = list(positions.keys())
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = keys[i], keys[j]
            sep = (positions[b] - positions[a]) % 360.0
            ang, orb = nearest_major_aspect(sep)
            if orb <= orb_policy(a, b, ang):
                hits.append((orb, f"{a:7s} — {b:7s}  {ang:>3}°  orb {orb:>4.2f}°"))
    if hits:
        for _, line in sorted(hits):
            print(line)
    else:
        print("(none within default orbs)")

if __name__ == "__main__":
    main()
# >>> AUTO-GEN END: Swiss Ephemeris Smoketest v1.0
