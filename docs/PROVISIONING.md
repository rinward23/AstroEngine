# >>> AUTO-GEN BEGIN: docs-provisioning v1.0
## Assets vs Data
- **Ephemeris assets** (Swiss data files) live outside the DB; we only *read* them.
- **User data** (natals, profiles, preferences) should live in your app store (e.g., app config DB).
- **Event packs** are computed from ephemeris on demand and can be materialized (SQLite/Parquet/ICS).

## First‑run provisioning
```bash
astroengine --provision-ephemeris
```

Writes `~/.astroengine/provision.json` with Swiss version and path. Enable strict gating:

```bash
astroengine --require-provision ...
```

## Precompute windows (desktop‑friendly)

```bash
astroengine \
  --start-utc 2025-01-01T00:00:00Z --end-utc 2025-12-31T00:00:00Z \
  --lunations --eclipses --stations --progressions --directions \
  --prog-aspects --dir-aspects --profections --natal-utc 1990-01-01T12:00:00Z --lat 40.7128 --lon -74.0060 \
  --precompute --export-sqlite out/astro.db --export-parquet out/astro-2025.parquet \
  --natal-id alice --profile default
```

Use this to ship a desktop app workflow where users explicitly **provision ephemeris** and **generate date windows** before querying.

# >>> AUTO-GEN END: docs-provisioning v1.0

