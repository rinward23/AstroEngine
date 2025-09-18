# AstroEngine Schema Contracts

The repository stores JSON schema definitions that mirror the
ruleset appendix contracts referenced by the AstroEngine
runtimes.  Operators can use the helper utilities in
`astroengine.validation` to run doctor-style validations before
launching a scenario.

## Schema directory

All schema payloads live under [`./schemas`](./schemas):

- `result_schema_v1.json` — structure for full run result
  payloads (channels, events, and provenance metadata).
- `contact_gate_schema_v2.json` — captures the gating decisions
  for near-threshold contacts and the evidence that justified
  them.
- `orbs_policy.json` — JSON resource describing the orb policy
  profiles that inform gating and scoring.

The JSON files live outside the Python modules to honor the
append-only ruleset workflow and to keep large data assets out
of the package namespace.

## Validation helpers

Two utility layers support schema validation:

- `astroengine.data.schemas` exposes a registry that resolves the
  JSON files to their on-disk locations.
- `astroengine.validation` provides a self-contained validator that
  understands the subset of JSON Schema used by the appendix contracts.
  Doctor scripts can call `validate_payload("result_v1", payload)` (or any
  other registered schema key) and receive actionable error messages without
  installing third-party packages.

### Running local validations

1. Validate a payload:

   ```python
   from astroengine.validation import validate_payload
   payload = {...}  # assembled from a run
   validate_payload("result_v1", payload)
   ```

2. (Optional) Install `pytest` and run the automated tests (these ship with
   representative sample payloads):

   ```bash
   pip install pytest
   pytest
   ```

The validation helpers are intentionally lightweight so they can
be embedded into existing “doctor” or pre-flight scripts without
risking accidental module removals.

# <<< AUTO-GEN START: CLI Usage v1.0 >>>
## CLI (demo)

Run the mock transit scan without a real ephemeris by invoking:

```bash
python -m astroengine.transit.cli scan-mock \
  --start 2025-01-01T00:00:00Z \
  --end 2025-01-31T00:00:00Z \
  --step 12 \
  --body Mars \
  --lon0 50 \
  --speed 6 \
  --natal-point Venus \
  --natal-lon 100 \
  --aspect square
```

The command uses a linear motion mock provider, so no external ephemeris is required for the demo run.
# <<< AUTO-GEN END: CLI Usage v1.0 >>>
