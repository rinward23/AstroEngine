# Rulepack Author (SPEC-B-008)

The Rulepack Author UI edits YAML/JSON rulepacks while validating against the schema from
[`rulepacks/schema.md`](../rulepacks/schema.md).

## Features

* **Schema-aware editor** — Inline validation powered by the JSON Schema snippet in the docs.
* **Diff view** — Compare the working copy with production rulepacks stored in Git.
* **Preview** — Execute the rulepack against the sample hits in Notebook 05.

## Tips

* Keep IDs lowercase with hyphen separators (`saturn-binding-growth`).
* Use `since:` to signal when a rule landed; the badge renders automatically in the docs.
* Run `python -m astroengine.ruleset_linter <path>` before committing.
