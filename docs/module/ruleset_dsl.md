# Ruleset DSL Grammar & Linter

- **Module**: `ruleset_dsl`
- **Author**: AstroEngine Ruleset Working Group
- **Date**: 2024-05-27
- **Source datasets**: Solar Fire ruleset exports (`rulesets/venus_cycle/rules.sfxml`), AstroEngine registry manifest (`astroengine/modules/registry.py`).
- **Downstream links**: DSL parser (`astroengine.rules.dsl.parser`), linter (`astroengine.rules.linter`), CLI `astroengine rules lint`.

## Grammar Specification (EBNF)

```
program         = statement* EOF ;
statement       = rule_decl | include_stmt | profile_override ;
rule_decl       = "rule" IDENTIFIER rule_header block ;
rule_header     = "when" predicate_list "then" action_list ["else" action_list] ;
include_stmt    = "include" STRING_LITERAL ";" ;
profile_override= "profile" IDENTIFIER "{" override_entry* "}" ;
override_entry  = IDENTIFIER ":" literal ";" ;
predicate_list  = predicate ("&&" predicate)* ;
predicate       = IDENTIFIER "(" arguments? ")" [comparator literal] ;
arguments       = expression ("," expression)* ;
action_list     = action ("," action)* ;
action          = IDENTIFIER "(" arguments? ")" ;
expression      = literal | IDENTIFIER | function_call ;
function_call   = IDENTIFIER "(" arguments? ")" ;
literal         = NUMBER | STRING_LITERAL | BOOLEAN | DURATION ;
comparator      = "==" | "!=" | ">" | ">=" | "<" | "<=" | "in" ;
BOOLEAN         = "true" | "false" ;
DURATION        = NUMBER ("d" | "h" | "m") ;
```

- `IDENTIFIER` tokens must map to registry module/submodule/channel names or predicate/action handles defined in `astroengine.rules.catalog`.
- `include` statements reference external DSL files stored under `rulesets/` and validated via SHA256 entries in `rulesets/index.yaml`.

## Predicate Catalogue

| Predicate | Arguments | Return type | Description | Gate phrase | Source |
| --------- | --------- | ----------- | ----------- | ----------- | ------ |
| `station` | `body`, `severity_band?` | `bool` | True when planetary station event exists within active window | "when {body} stations" | Solar Fire station triggers |
| `ingress` | `body`, `sign` | `bool` | Sign ingress detection | "when {body} enters {sign}" | Solar Fire ingress rules |
| `combust` | `body`, `orb?` | `bool` | Checks combustion state using orb policy table | "when {body} is combust" | Solar Fire combustion config |
| `oob` | `body` | `bool` | Out-of-bounds declination | "when {body} is out of bounds" | Solar Fire declination gate |
| `aspect` | `transit_body`, `natal_body`, `aspect_family`, `orb_override?` | `bool` | Longitude/declination aspects leveraging `core-transit-math` matrix | "when {transit} {aspect} {natal}" | Solar Fire aspect trigger exports |
| `midpoint` | `pair_id`, `transit_body`, `orb?` | `bool` | Midpoint activation | "when {transit} hits {pair} midpoint" | Solar Fire midpoint file |
| `fixed_star` | `star_id`, `body`, `orb?` | `bool` | Fixed star contact | "when {body} contacts {star}" | FK6 catalogue mapping |
| `progression` | `event_kind`, `profile_id?` | `bool` | Secondary progression events | "when progressed {event}" | Solar Fire progression table |
| `direction` | `event_kind`, `promissor`, `significator` | `bool` | Primary direction events | "when directed {promissor} meets {significator}" | Solar Fire directions |
| `severity_band` | `band` | `bool` | Checks severity classification | "when severity is {band}" | Derived from severity module |

Each predicate logs dataset URNs in evaluation output to verify the trigger is backed by actual Solar Fire or Swiss Ephemeris data.

## Type System

- `body`: enumerated string (`sun`, `moon`, `mercury`, etc.).
- `sign`: enumerated string (`aries` … `pisces`).
- `aspect_family`: enumerated string referencing `core-transit-math` aspect canon.
- `star_id`: ID referencing FK6 dataset row.
- `pair_id`: composite identifier `<body1>_<body2>` referencing midpoint table.
- `severity_band`: enumerated string (`weak`, `moderate`, `strong`, `peak`).
- `event_kind`: enumerated string per event module (e.g., `station_retrograde`, `solar_eclipse_total`).
- Literals support ISO-8601 durations (`14d`, `6h`) and numeric thresholds.

## Error Taxonomy

| Error code | Condition | Example | Remediation |
| ---------- | --------- | ------- | ----------- |
| `AE1001` Unknown predicate | Predicate not found in catalog | `predicate foobar()` | Check `docs/module/ruleset_dsl.md` predicate table; add via governance if legitimate |
| `AE1002` Arity mismatch | Wrong number of arguments | `ingress(mars)` | Supply required `sign` argument |
| `AE1003` Type mismatch | Argument type incompatible | `aspect("mars", 5, "square")` | Use body identifier rather than numeric literal |
| `AE1004` Unknown identifier | Body/sign/ID missing from registry | `aspect(chiron, sun, conjunction)` | Register dataset and update registry manifest |
| `AE1005` Orb out of bounds | Orb override narrower than zero or wider than allowed | `aspect(mars, sun, conjunction, orb=-1)` | Adjust value to positive degrees |
| `AE1006` Unreachable gate | Condition can never be true because dependencies absent | `station(pluto) && direction(primary,...)` in profile without directions enabled | Add dependency module or remove gate |
| `AE1007` Missing export | Rule lacks export action | `rule foo when ingress(mars, leo) then notify()` without export mapping | Append `export("astrojson", template_id)` |
| `AE1008` Provenance missing | Dataset lacks checksum | `fixed_star(spica, sun)` when FK6 table missing hash | Restore dataset index and rerun environment validator |

## Linter Rules

1. **Module integrity**: verify every predicate/action references a registered module/submodule/channel; fail if any reference is missing to prevent accidental module loss.
2. **Severity coverage**: ensure each ruleset defines handling for `strong` and `peak` severity bands; warn for missing `weak` coverage.
3. **Profile parity**: check that each profile override block references an existing profile ID recorded in `profiles/index.yaml`.
4. **Export completeness**: for every rule, verify at least one `export()` action referencing AstroJSON/CSV/ICS channels documented in `docs/module/interop.md`.
5. **Dataset checksum alignment**: ensure referenced dataset URNs exist in `docs/module/data-packs.md` provenance tables with matching checksums.
6. **Determinism**: detect use of random or time-of-lint constructs; reject `now()` or environment-dependent functions without explicit seeding.
7. **Redundant gates**: flag rules where predicate combinations are strict supersets of another rule, preventing contradictory alerts.

## Observability

- Parser emits `dsl_parse` events with `rule_id`, `source_file`, `checksum`, and success state.
- Linter outputs JSONL entries listing violations, dataset URNs, and remediation guidance so QA can trace issues to Solar Fire exports.

Maintaining this grammar and linter specification ensures the DSL stays aligned with authenticated datasets and that module hierarchies remain intact throughout future revisions.
