<!-- >>> AUTO-GEN BEGIN: Ruleset Linter v1.0 (instructions) -->
Purpose: static checks for ruleset YAMLs.

Checks:
- Unknown module ids; duplicate ids; missing `channels` keys.
- Gate expression validation: unknown predicates, mismatched parentheses, unused variables.
- Overlapping gates producing identical families; missing caps (`family_cap_per_day/week`).
- Orphan exports (no events emitted for module).
- Profile references that do not exist.
- Severity range enforcement [0,1]; partile rule present for aspect modules.

Outputs:
- Lint summary with file:line; severity (ERROR/WARN/INFO); fix-suggestions.
- CI mode: fail on ERROR; warn on WARN.
<!-- >>> AUTO-GEN END: Ruleset Linter v1.0 (instructions) -->
