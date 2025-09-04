# Ruleset Consolidation Package

This package rebuilds a coherent **append-only** ruleset from *all* past iterations (YAML/JSON), selecting the latest version of each module by ISO timestamp and producing a single canonical set, plus lineage & validation reports.

## Files included

- `consolidate_rulesets.py` — one-shot consolidator script
- `templates/module_template.yaml` — recommended header/body shape
- `scripts/precommit_append_only.sh` — Git pre-commit guard for append-only naming
- `.github/workflows/consolidate-ruleset.yml` — optional CI to run validation on pushes/PRs
- `.gitignore` — ignores build outputs and common artifacts
- `Makefile` — convenience targets

## Quick start

1. **Install dependencies**
   ```bash
   pip install pyyaml
   ```

2. **Create input folder and copy *all* iterations**
   ```bash
   mkdir -p ./_incoming_all_iterations
   # Put every YAML/JSON iteration there (subfolders OK)
   ```

3. **Run consolidation**
   ```bash
   python3 consolidate_rulesets.py --in ./_incoming_all_iterations --out ./rulesets --single
   ```

4. **Review outputs**
   - `rulesets/_reports/RULESET__VALIDATION_*.md` — parsing issues, missing modules
   - `rulesets/_reports/RULESET__MANIFEST_*.csv` — full lineage & “latest” selection
   - `rulesets/overrides/*.yaml` — latest version per module (append-only file names)
   - `rulesets/ruleset.main.yaml` — combined single-file view

## Required modules

The script fails if any of these are missing in the final selection:
- `aspects`, `transits`, `scoring`, `narrative`

## Header requirements (per module file)

Each YAML/JSON file should include at least:
```yaml
id: <module-id>            # e.g., aspects | transits | scoring | narrative | other-id
name: <human title>
version: 2025-09-03T22:41Z # ISO-like; latest timestamp wins
status: active             # or supersedes
supersedes: <id-or-file>   # optional but helpful for lineage
# ... body follows ...
```

## Git append-only guard

To prevent accidental in-place edits, install the pre-commit hook:
```bash
cp scripts/precommit_append_only.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

The hook blocks commits that modify files in `rulesets/overrides/` unless the filename contains a timestamp pattern `__vYYYYMMDD-HHMM.yaml` and is *new*, not edited in place.

## CI (optional)

Enable the GitHub Actions workflow by committing `.github/workflows/consolidate-ruleset.yml`. It will run the consolidator and fail if required modules are missing.

## Make targets

- `make consolidate` — run the consolidator (edit paths via variables at top of Makefile)
- `make clean` — remove generated outputs

## Tips for 70+ input files

- It’s OK if some older files are malformed; see the Validation report for exact errors.
- If a module has two files with the same `version`, the latest by sort order is chosen. You can bump the `version` in the intended latest file to force selection.
- You can re-run the script as many times as needed; it never overwrites your originals, only writes new timestamped outputs.
 
