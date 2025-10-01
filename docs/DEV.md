# >>> AUTO-GEN BEGIN: DEV Bootstrap v1.0
## Local Git hygiene

- Enable Git to remember conflict resolutions you make once:
  ```bash
  git config --global rerere.enabled true
  ```

- Prefer rebases over merge commits when pulling:
  ```bash
  git config --global pull.rebase true
  git config --global rebase.autoStash true
  ```

## Pre-commit hooks

Install once per clone:

```bash
make hooks
```

This adds a *merge-conflict* check so commits fail if `<<<<<<<`, `=======`, `>>>>>>>` markers exist.

## Repo git hooks

```bash
bash scripts/setup_git_hooks.sh
```

This sets Git to use the repo-managed `pre-commit` and `pre-push` hooks automatically.

## Cleanup helpers

Keep branches free from generated clutter:

```bash
make clean        # remove lightweight caches
make deepclean    # invoke scripts/cleanup/repo_clean.py --deep
```

`deepclean` trims trailing whitespace in tracked text assets and purges build
artefacts (node_modules, .pytest_cache, etc.) while leaving the module →
submodule → channel → subchannel hierarchy intact.  Dataset stores such as
`datasets/`, `profiles/`, `rulesets/`, and `astroengine/data/` are explicitly
excluded from text normalisation so reference ephemerides remain untouched.

## Typical update flow

```bash
# Keep feature branch fresh before committing/pushing
git fetch origin
git rebase --rebase-merges origin/main
# fix if prompted, run tests
make lint
```

# >>> AUTO-GEN END: DEV Bootstrap v1.0
