# Licensing & Ephemeris Data

Swiss Ephemeris data is not redistributed with this repository. Use the following strategy:

1. Download the licensed Swiss Ephemeris files from Astrodienst.
2. Mount them in production and set `SE_EPHE_PATH` accordingly.
3. For tests and docs, the stub at `datasets/swisseph_stub` is sufficient.

See the root `docs/SWISS_EPHEMERIS.md` in this repository for installation details.
