from datetime import UTC, datetime, timedelta

from core.stars_plus.aspects import find_star_aspects
from core.stars_plus.catalog import load_catalog
from core.stars_plus.geometry import mean_obliquity_deg, radec_to_ecliptic_lon_deg
from core.stars_plus.parans import Location, ParanPair, detect_parans

POLICY = {"per_object": {}, "per_aspect": {"conjunction": 1.0, "opposition": 1.0, "square": 1.0, "trine": 1.0, "sextile": 1.0}, "adaptive_rules": {}}


def test_radec_to_ecliptic_basic():
    ts = datetime(2025, 1, 1, tzinfo=UTC)
    eps = mean_obliquity_deg(ts)
    # RA=0, Dec=0 → λ≈0
    lam0 = radec_to_ecliptic_lon_deg(0.0, 0.0, eps)
    assert abs(lam0 - 0.0) < 1e-6
    # RA=90, Dec=0 → λ≈90
    lam90 = radec_to_ecliptic_lon_deg(90.0, 0.0, eps)
    assert abs(lam90 - 90.0) < 1e-6


def test_star_aspect_square_synthetic():
    ts = datetime(2025, 1, 1, tzinfo=UTC)
    stars = load_catalog()
    # Force a star with ecliptic longitude near 90 (use RA=90,Dec=0 by injecting temp star)
    stars["TestStar"] = type("S", (), {"name":"TestStar","ra_deg":90.0,"dec_deg":0.0,"vmag":1.0})()
    planet_lons = {"Sun": 0.0}
    hits = find_star_aspects(ts, planet_lons, stars, aspects=["square"], policy=POLICY, mag_max=2.5)
    assert any(h["star"] == "TestStar" and h["planet"] == "Sun" and h["aspect"] == "square" for h in hits)


def test_paran_rise_culminate_equator_synthetic():
    # Equator site, star RA=0,Dec=0 (rises at LST=-90°), planet culm when LST=planet RA
    loc = Location(lat_deg=0.0, lon_east_deg=0.0)
    stars = {"TestStar": type("S", (), {"name":"TestStar","ra_deg":0.0,"dec_deg":0.0,"vmag":1.0})()}

    # Planet RA chosen so that its culmination coincides with star rising within tolerance
    def provider_radec(ts, name):
        return (270.0, 0.0)  # RA=270° so LST=270 matches star rising (α=0,H=-90 → LST=270)

    start = datetime(2025, 1, 1, tzinfo=UTC)
    end = start + timedelta(days=1)
    pairs = [ParanPair(star_name="TestStar", planet_name="Mercury", star_event="rise", planet_event="culminate")]

    events = detect_parans(start, end, loc, stars, provider_radec, pairs, tol_minutes=10.0)
    assert len(events) >= 1
    e = events[0]
    assert e.kind == "paran" and e.meta["star"] == "TestStar" and e.meta["planet"] == "Mercury"
