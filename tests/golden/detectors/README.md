# Detector Golden Outputs

These fixtures capture canonical detector outputs sourced from the Solar Fire
comparison exports documented under `docs-site/docs/fixtures/` and
`qa/artifacts/solarfire/2025-10-02/`. Each JSONL file records the
canonicalised event payload produced by AstroEngine when replaying the Solar
Fire export for the referenced scenario.

- `timeline_mars_saturn.jsonl` reproduces the Mars–Saturn conjunction timeline
  hit used throughout the notebooks (`docs-site/docs/cookbook/08_timeline.ipynb`).
- `timeline_mars_saturn.sha256` stores the SHA-256 checksum of the canonical
  serialisation used by the regression test.

To update these fixtures, regenerate the Solar Fire derived datasets under
`docs-site/docs/fixtures/` (see `docs-site/scripts/exec_notebooks.py`) and
recompute the canonical JSONL plus checksum using the helper described in
`docs/module/qa_acceptance.md`.
