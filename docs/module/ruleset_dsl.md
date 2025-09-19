# Ruleset Authoring Notes

- **Module**: `ruleset_dsl`
- **Maintainer**: Ruleset Working Group
- **Source artifacts**:
  - Markdown rulesets in `rulesets/transit/`
  - Runtime registry in `astroengine/modules/vca/__init__.py`
  - Severity and orb documentation in `docs/module/core-transit-math.md`

A dedicated DSL parser has not been committed yet. Instead, the repository stores human-readable ruleset outlines in Markdown (see `rulesets/transit/*.ruleset.md`). This document captures the conventions those outlines follow so that when a parser is introduced it can map back to the same module/submodule/channel/subchannel identifiers without loss.

## Current structure

- Each Markdown file starts with an `AUTO-GEN[...]` header describing the module path (e.g., `transit.stations`, `transit.scan`).
- Sections such as `DATA DEPENDENCIES`, `PIPELINE LAYERS`, and `DETERMINISM REQUIREMENTS` mirror the values recorded in `profiles/base_profile.yaml` and `docs/module/core-transit-math.md`.
- The prose references the planned detector channels documented in `docs/module/event-detectors/overview.md`.

## Transition plan for a formal DSL

When implementing the parser and linter:

1. **Token vocabulary** — derive predicate and action names from the existing Markdown sections. For example, station detection uses inputs described under `DATA SOURCES` and actions outlined in `DETECTION LOGIC`.
2. **Module mapping** — ensure every rule encodes its module path using the placeholders listed in `docs/module/event-detectors/submodules/README.md` so registry integrity is preserved.
3. **Dataset references** — require explicit references to real files (`profiles/base_profile.yaml`, `profiles/fixed_stars.csv`, `schemas/orbs_policy.json`) rather than synthetic identifiers. Record updates in `docs/governance/data_revision_policy.md` when those datasets change.
4. **Validation** — add pytest coverage that round-trips the Markdown source into DSL structures and back, verifying that no gates are lost and that severity/orb values match the documentation.

## Authoring guidelines

- Keep Markdown rulesets in sync with the data packs documented in `docs/module/data-packs.md`, citing Solar Fire or Swiss Ephemeris exports wherever numeric values originate.
- Record any new predicates or actions in this file along with the backing dataset so governance can track additions.
- When the DSL lands, maintain backward-compatible aliases for existing identifiers so historical rulesets can still be parsed.
- Before publishing changes, export the relevant scenario from Solar Fire and attach the checksum to the ruleset’s header so the runtime can prove the rule references real data.

By documenting the current approach and the migration path, we ensure the future DSL remains anchored to the real data shipped in this repository and that module integrity is maintained throughout the transition.
