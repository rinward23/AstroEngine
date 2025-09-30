# Outer-Cycle Analytics (Submodule C-043)

**Channels:** `cycles.pairs`, `cycles.search`, `ingresses.detection`,
`ingresses.timeline`, `triggers.entity`, `triggers.severity`

## Overview

Extends the SPEC-0 aspect engines to deliver mundane-focused timelines for outer
planet combinations (Saturn, Jupiter, Uranus, Neptune, Pluto). It documents
cycle computations, ingress detection, and entity trigger sweeps, ensuring
results can be reconciled against Solar Fire transits and authoritative
almanacs.

## Cycle Detection

* `cycles.pairs` defines supported pairings, harmonic families, and default
  aspect sets (conjunction, opposition, square, trine, sextile, semi-square,
  sesquiquadrate).
* `cycles.search` orchestrates calls into the dynamic aspect search engine,
  streaming results into `outer_hits` table with metadata (severity, retrograde,
  speed differentials).
* Time ranges default to 1800–2200 but accept narrower windows per request.

## Ingress Detection

* `ingresses.detection` tracks sign changes for outer planets, capturing degree,
  sign, motion direction, and station flags.
* `ingresses.timeline` groups ingresses into sequences for visualization and
  exports to CSV/GeoJSON.
* All timestamps remain in UTC with fractional seconds when required.

## Entity Trigger Sweeps

* `triggers.entity` loops through entity charts (from the registry) and computes
  aspects between transiting outers and key natal points (Sun, Moon, ASC, MC,
  angles) within configured orbs.
* `triggers.severity` assigns weights based on orb tightness, body significance,
  and applying/separating status using SPEC-0 severity models.
* Outputs stored in `entity_triggers` include event metadata, aspect, orb,
  severity band, and provenance fields referencing the natal chart checksum.

## APIs

* `POST /mundane/cycles/search` accepts body pairs, aspect families, and time
  range; returns job ID and later results via polling or websocket channel.
* `POST /mundane/ingresses/search` accepts list of bodies and date range.
* `POST /mundane/triggers/scan` ingests entity lists (or `all`) and scheduling
  parameters, supporting resumable jobs via Redis queues.

## Data Integrity

* All calculations must reference the same ephemeris set as Solar Fire (Swiss
  Ephemeris or NASA JPL) with recorded version and checksum.
* Severity policies link to rulesets documented in `docs/module/core-transit-math.md`.
* Each trigger stores `source_run_id`, ephemeris version, orb policy, and profile
  ID to guarantee reproducibility.

## Performance & Caching

* Use incremental stepping with root-finding to converge on exact aspect times.
* Cache repeated cycle searches per `(pair, aspects, range, policy)` key for 12
  hours in Redis.
* Batch entity triggers by timezone to reuse ephemeris sweeps, streaming results
  to PostgreSQL via COPY for efficiency.

## Testing & Validation

* Unit tests assert conjunction/opposition sequences for Jupiter-Saturn match
  published dates (e.g., 1842, 1861, …, 2020).
* Integration tests compare ingress detection with Solar Fire exports for recent
  outer planet sign changes.
* Trigger regression harness cross-checks severity scores against curated Solar
  Fire mundane reports.

## Dependencies

* Requires access to SPEC-0 dynamic aspect engine APIs.
* Depends on National Charts Registry for natal chart metadata and Historical
  Geo-Temporal Mapping for timezone verification.
* Outputs consumed by Mundane Dashboard timeline overlays and CSV exports.

