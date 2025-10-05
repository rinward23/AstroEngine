# Swiss Ephemeris Stub Directory

This directory ships with the AstroEngine wheel so downstream installations always have
a deterministic fallback ephemeris path.  The stub intentionally does **not** include
any of the proprietary Swiss Ephemeris `.se1` data files; when those are available,
place them in this directory or point `SE_EPHE_PATH` to the folder containing them.

During development the repository root also contains `datasets/swisseph_stub`, which
mirrors this packaged directory.  Tooling (tests, docs, bootstrap scripts) resolves the
packaged location automatically when the repository datasets folder is absent.
