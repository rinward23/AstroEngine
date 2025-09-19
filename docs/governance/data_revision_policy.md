# Data Revision Policy

This policy replaces the previous "append-only" rule with a controlled
revision workflow.  Contributors may edit existing datasets and schemas as
long as the changes are logged and traceable to verifiable SolarFire or
runtime evidence.  The goal is to keep merge conflicts manageable without
risking the accidental removal of modules, channels, or subchannels.

## Guiding principles

1. **Preserve hierarchy:** the module → submodule → channel → subchannel
   structure remains canonical.  Updates must not delete existing nodes;
   deprecations should mark entries with `status: deprecated` metadata
   instead of removing them.
2. **Log every edit:** each mutable asset maintains a `revision_log`
   section that records the revision identifier, author, timestamp, and
   provenance reference (dataset URN, SolarFire export hash, QA notebook
   URL, etc.).
3. **Make edits surgical:** update only the fields that change.  Avoid
   reformatting unrelated lines so rebases remain small and conflicts are
   simple to resolve.
4. **Back every value with data:** never introduce synthetic values.
   Revisions must reference real exports, calculations, or validated
   observations.

## Applying revisions to JSON schemas

When a schema stored in `./schemas` needs to change, edit the existing
file in place and append an entry to its `revision_log` array:

```json
{
  "title": "result_schema_v1",
  "type": "object",
  "properties": {
    "score": {"type": "number"}
  },
  "required": ["score"],
  "revision_log": [
    {
      "revision": "2024-06-02-fix-score-bounds",
      "author": "astroengine-governance",
      "reason": "Align upper bound with SolarFire QA export 2024-05-29",
      "source": "urn:solarfire:qa:2024-05-29:result-batch-17"
    }
  ]
}
```

The runtime keeps schemas outside the Python package so these edits do not
invalidate module imports.  Because git tracks every change, the `revision`
identifier only needs to be unique within the file.

## Applying revisions to CSV or SQLite datasets

- **CSV**: Add or update rows directly, but include a `revision` column
  that stores the revision identifier.  Existing rows may be corrected by
  changing their non-key fields and bumping the `revision` value.
- **SQLite**: Maintain a `revisions` table that records revision IDs,
  timestamps, and change descriptions.  Data tables should include a
  `revision_id` foreign key referencing the latest applicable revision.

For bulk updates, create a companion Markdown note under
`docs/module/<module>/changes/REVISION_ID.md` summarising the affected
channels and subchannels.  This keeps humans aligned without forcing
append-only data churn.

## Tooling support

- The `astroengine.modules.registry` API already supports metadata updates
  without deleting nodes.  When updating metadata through Python code,
  ensure you merge dictionaries instead of replacing them wholesale.
- Future automated tooling (migrations, validation scripts) should read
  the `revision_log` sections to produce audit reports.

## Review checklist

Before merging a pull request that edits datasets or schemas, reviewers
should confirm:

1. The module hierarchy is intact and no nodes disappeared.
2. Every changed asset documents a new `revision_log` entry.
3. All referenced data sources are real and reproducible (provide hashes
   or URNs when possible).
4. Tests and validators (`pytest`, schema validators) still pass.

Following this policy allows targeted updates without losing history or
accidentally dropping modules, while keeping merge conflicts contained.
