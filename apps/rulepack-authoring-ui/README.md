# Rulepack Authoring UI

This Next.js application provides an authoring environment for AstroEngine interpretation rulepacks. It combines a schema-aware YAML/JSON editor, semantic linting, live previews against the Interpretations API, and version comparison tools.

## Getting started

```bash
cd apps/rulepack-authoring-ui
npm install
npm run dev
```

Set the following environment variables in a `.env.local` file to connect with backend services:

```
NEXT_PUBLIC_INT_API=https://api.example.com
NEXT_PUBLIC_REL_API=https://api.example.com
# Optional
NEXT_PUBLIC_API_KEY=your-token
```

## Key features

- **Monaco editor** with YAML/JSON switch, schema validation using the bundled draft 2020-12 schema, and local persistence backed by IndexedDB via `localForage`.
- **Semantic lint panel** detecting duplicate IDs, unknown bodies/tags, invalid severities, and potential conflicts.
- **Live preview** sending the current draft to the Interpretations API, with optional synastry hit computation through the Relationship API.
- **Version history** showing saved rulepacks from the API and an inline diff viewer against the current draft.
- **Rule snippet catalogue** for quickly inserting frequently used structures.

## Testing

```bash
npm run lint
npm run typecheck
npm run test
```

Vitest is configured for future unit tests. The lint/typecheck commands verify the React/TypeScript surface.
