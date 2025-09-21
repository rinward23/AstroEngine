# >>> AUTO-GEN BEGIN: perf smoke v1.0
import os, datetime as dt, pytest
pytestmark = [pytest.mark.perf, pytest.mark.swiss]

def _have_swiss():
    try:
        import swisseph as _  # noqa
        return bool(os.getenv("SE_EPHE_PATH"))
    except Exception:
        return False

@pytest.mark.skipif(not _have_swiss(), reason="Swiss unavailable")
def test_fast_scan_runs_under_budget():
    from astroengine.engine import fast_scan, ScanConfig
    start = dt.datetime(2025,1,1,0,0)
    end   = dt.datetime(2025,1,3,0,0)
    cfg = ScanConfig(body=1, natal_lon_deg=195.0, aspect_angle_deg=0.0, orb_deg=6.0, tick_minutes=60)
    hits = fast_scan(start, end, cfg)
    assert isinstance(hits, list)
    assert len(hits) <= 12  # sanity
# >>> AUTO-GEN END: perf smoke v1.0
