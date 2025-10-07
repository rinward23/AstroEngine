# Swiss Ephemeris Stub Directory

This directory is intentionally empty.  Tests set the `SE_EPHE_PATH`
environment variable to this path so that PySwissEph falls back to its
built-in Moshier calculations when full Swiss ephemeris files are not
available.  In production deployments replace this directory with the
real Swiss data pack from Astrodienst.

When the project is installed from a wheel, the same stub lives under
`astroengine/datasets/swisseph_stub`.  Tooling resolves whichever copy is
present so you can drop licensed `.se1` data into either location.
