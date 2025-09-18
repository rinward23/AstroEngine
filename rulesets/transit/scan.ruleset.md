```AUTO-GEN[transit.scan]
SUMMARY
  - Execute the umbrella transit scan pipeline responsible for coordinating station, ingress, lunation, declination, and auxiliary detectors under the module → submodule → channel → subchannel hierarchy demanded by the runtime schemas.
  - Guarantee deterministic ordering by primary timestamp (UTC, ISO8601) and secondary severity score; emit determinism hash inputs sorted before hashing.

DATA DEPENDENCIES
  - Ephemeris providers: must supply barycentric positions, velocities, ecliptic longitudes/latitudes, right ascension/declination, speed status, and phase angles for Sun → Sedna, lunar nodes, and Earth-Moon barycenter sampled at ≤6h cadence for inner bodies (Sun, Moon, Mercury, Venus, Mars, Ceres, Pallas, Juno, Vesta) and ≤24h for Jupiter → Sedna and nodes.
  - Natal dataset: ingest birth timestamp (UTC), geographic coordinates, house system selection, profile toggles, and pre-computed natal positions for all enabled bodies/points; cross-reference with natal hash for audit.
  - Indexed reference tables: dignities.csv, fixed_stars.csv, benefic/malefic multipliers, declination thresholds, antiscia lookup pairs, midpoint definitions; each table versioned with checksum fields.

PIPELINE LAYERS
  - Module `transit.scan`: orchestrator; resolves active profile, provider, and techniques; seeds caches for ephemeris samples, timezone conversions, fixed star positions, midpoint targets, and antiscia mirrors.
  - Submodules:
      * `transit.stations`: retrograde/direct detection feed (see dedicated ruleset).
      * `transit.ingresses`: sign boundary detection feed.
      * `transit.lunations`: new/full/quarter moon and eclipse detection feed.
      * `transit.declination`: out-of-bounds and declination aspect detectors.
      * `transit.aux`: antiscia, midpoints, fixed stars, combustion/under-beams, timing overlays (returns, profections) gated by profile toggles.
  - Channel Requirements: each submodule must emit events under a canonical channel key (e.g., `stations`, `ingresses`, `lunations`, `declination`, `overlays`) with deterministic subchannel naming (e.g., `retrograde`, `direct`, `solar`, `lunar`, `oob_enter`, `antiscia_exact`).

EXECUTION FLOW (PSEUDOCODE)
  1. Load profile → feature flags → severity/orb policies; verify schema version compatibility.
  2. Build ephemeris cache window covering scan start/end ± 3 days buffer for interpolation and retrograde boundary detection.
  3. Query provider for vectorized samples at configured cadence; store in deterministic cache keyed by (body_id, timestamp, frame).
  4. For each enabled detector submodule:
        a. Request required data slices (positions, speeds, declinations, etc.).
        b. Run detector-specific logic to produce candidate events.
        c. Deduplicate by (body_id, timestamp, channel, subchannel) hash.
        d. Hydrate event metadata: natal cross-checks (closest natal body/angle distance), orb distances, severity weight, provenance (ephemeris sample IDs, profile flag names), determinism hash inputs.
  5. Merge all events, sort (timestamp, severity desc, body_id), compute determinism hash (SHA-256 of canonical JSON serialization), and emit to downstream schema validator.
  6. Persist structured logs (JSON) documenting provider sample counts, cache hits, total events, filtered events, and determinism hash.

VALIDATION & LOGGING
  - Schemas: events must validate against `schemas/events/transit_event.schema.json`; run determinism test (hash must match repeated run with identical inputs).
  - Logging fields: `module`, `submodule`, `channel`, `subchannel`, `body_id`, `severity`, `orb`, `provider_sample_ids`, `profile_flags`, `natal_ref`, `hash_inputs`.
  - Errors: classify as `CONFIG_ERROR`, `PROVIDER_ERROR`, `DATA_GAP`, or `COMPUTE_ERROR`; `PROVIDER_ERROR` must include retriable flag.

PROFILE INTEGRATION
  - Respect toggles for stations, ingresses, lunations, declination aspects, antiscia, midpoints, fixed stars, profections, returns, progressions, timelords, maps, draconic, sidereal, house systems, minor/dwarf bodies.
  - Orb/severity policies pulled from profile tables; fallback to defaults only when profile explicitly omits entry.
  - Draconic/sidereal modes require alternative coordinate frames; ensure provider exposes necessary transforms (Astropy/ERFA fallbacks).

DETERMINISM REQUIREMENTS
  - Hash seed includes: profile_id, provider_id, schema_version, time_window, sorted event payloads.
  - Cache directories keyed by provider/version/profile/time_window; verify checksum before reuse.
  - No random sampling; all filters deterministic and data-backed.
```
