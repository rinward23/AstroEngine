# Settings Snapshot Schema Versioning

- Added an explicit `schema_version` marker to persisted settings snapshots and `/v1/settings` responses so that historical chart runs can declare which schema they rely on.
- The settings loader now normalises legacy payloads by stamping the current schema version and resaving `config.yaml`, ensuring previously exported bundles continue to load without manual edits.
- No manual migration steps are required; existing installations will be updated the next time the configuration file is read.
