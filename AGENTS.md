# AstroEngine Contribution Guide

## Scope
These instructions apply to the entire repository unless a more specific `AGENTS.md` is added deeper in the tree.

## Architectural Expectations
- Preserve the module → submodule → channel → subchannel organization already established under `astroengine/`. Introduce new capabilities by extending this hierarchy instead of replacing or removing existing modules unless explicitly requested by the user.
- When touching data-backed workflows (CSV, SQLite, or other data stores), ensure every produced value is derived from real sources available to the project. Never substitute placeholder or synthetic astrology results.
- Keep smoketests and diagnostics deterministic; if you modify a script that emits ephemeris or chart data, ensure it documents the provenance of the data it reports.

## Coding Style
- Prefer readable, well-documented Python. Follow existing naming patterns in the touched module; avoid introducing broad formatting changes unrelated to the task.
- Place shared utilities inside the relevant module hierarchy rather than at the project root, and accompany substantive features with docstrings or inline comments summarizing their intent.

## Testing & Verification
- Run `pytest` after any change that could affect Python code or dependencies. Include the command and its status in the testing section of the final response.
- If you touch automation under `.github/` or scripts under `scripts/`, exercise the most relevant command (for example, invoking a smoketest) when practical and document the result.

## Documentation
- Update `README.md`, `docs/`, or module-specific documentation whenever behavior, inputs, or outputs change in a way users should know about.
- Keep instructions for obtaining external datasets (e.g., Swiss Ephemeris files) accurate and reproducible.

## Git & PR Hygiene
- Keep the working tree clean before finishing. Do not rewrite existing commits; add new ones as needed.
- Reference this guide when clarifying contribution expectations in discussions or reviews.
