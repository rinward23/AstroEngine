>>> AUTO-GEN BEGIN: Docs Repos Plan v1.0

Companion Repos (create when ready)

1) astroengine-data (public)

Canonical catalogs loaded at runtime.

modules/
  bodies.yml           # ids, categories, default orbs
  aspects.yml          # angles, canonical names
  dignities.yml        # rulership/exaltation/detriment/fall
  ayanamsa.yml         # named presets
fixed_stars.csv        # name, RA, Dec, mag, spectral
correspondences/       # VCA ↔ Tarot/Kabbalah/Chakras mappings

Notes: do not commit Swiss ephemeris binaries. Engine reads from SE_EPHE_PATH.

2) astroengine-profiles (public)

Profiles for orb policy, severity weights, VCA domain weights, versioned.

3) astroengine-docs (public)

Docs site (MkDocs Material). Optionally mirror docs/ here and publish via Pages.

Optional soon

astroengine-examples (CLI/Jupyter demos)

astroengine-registry (JSON index of plugins with semver)


>>> AUTO-GEN END: Docs Repos Plan v1.0
