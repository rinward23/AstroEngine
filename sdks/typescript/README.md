# AstroEngine TypeScript SDK

This workspace packages the `@astroengine/sdk` client referenced by
`docs/module/developer_platform/sdks.md`. It relies on PNPM for dependency
management and on versioned OpenAPI payloads stored under `openapi/` in the
repository root.

## Commands

- `pnpm --filter sdks/typescript install` — install dependencies.
- `pnpm --filter sdks/typescript generate --schema ../../openapi/v1.0.json` —
  parse the schema, rebuild typed operation descriptors, and update
  `CHANGELOG.md` with the schema and dataset hashes used for the release.
- `pnpm --filter sdks/typescript build` — build ESM and CJS bundles to `dist/`.
- `pnpm --filter sdks/typescript test` — run the Vitest contract suite.

The generator and tests are deterministic; they expect the Solar Fire and Swiss
Ephemeris stub files in `datasets/` to exist so release metadata can be
recorded. When the real datasets are mounted the recorded hashes reflect those
artefacts instead of the stub readmes.
