# >>> AUTO-GEN BEGIN: swe smoketest v1.0
#!/usr/bin/env python
import os
import sys

try:
    from astroengine.ephemeris.swe import swe
    ok = True
except Exception as e:
    print("ERROR: pyswisseph import failed:", e)
    sys.exit(2)

path = os.environ.get("SE_EPHE_PATH")
if path and os.path.isdir(path):
    swe().set_ephe_path(path)
print("pyswisseph:", getattr(swe, "__version__", "ok"))
print("SE_EPHE_PATH:", path or "(unset)")
print("JD(2000-01-01 UT):", swe().julday(2000, 1, 1, 0.0))
sys.exit(0)
# >>> AUTO-GEN END: swe smoketest v1.0
