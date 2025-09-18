<!-- >>> AUTO-GEN BEGIN: Ruleset DSL Grammar v1.0 (instructions) -->
Grammar (sketch)
- expr := or_expr
- or_expr := and_expr { 'or' and_expr }
- and_expr := unary_expr { 'and' unary_expr }
- unary_expr := ['not'] primary
- primary := literal | ident | call | '(' expr ')'
- call := ident '(' [args] ')'
- args := expr { ',' expr }
- literal := number | string | list
- list := '[' [expr { ',' expr }] ']'
- comparators: == != < <= > >=
- identifiers: [A-Za-z_][A-Za-z0-9_]*

Types
- number (float), string, bool, list, datetime (ISO string), enum (aspect names, bodies).

Predicates (minimum set)
- is_station, in_shadow, is_ingress, is_lunation, is_eclipse, is_cazimi/combust/under_beams,
  is_oob/oob_transition, is_parallel/contraparallel, is_antiscia/contra_antiscia,
  hit_midpoint, hit_fixed_star, near, within_orb, is_angle, has_dignity, is_day_chart, phase,
  family_cap_per_day, family_cap_per_week.

Errors & Lint
- Unknown predicate, wrong arity, type mismatch, unreachable due to always‑true/false sub‑exprs, missing caps.

Examples
- family_cap_per_day(3) and ((aspect in [conjunction, opposition, square] and severity >= 0.65) or (aspect in [trine, sextile] and transiting_body in [Jupiter, Venus]))
- is_station(Mercury, retro) or (is_ingress(Mars) and is_angle(natal_point))
- is_lunation(full) and near(ASC, 3)
<!-- >>> AUTO-GEN END: Ruleset DSL Grammar v1.0 (instructions) -->
