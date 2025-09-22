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

## Typical update flow

```bash
# Keep feature branch fresh before committing/pushing
git fetch origin
git rebase --rebase-merges origin/main
# fix if prompted, run tests
make lint
```

# >>> AUTO-GEN END: DEV Bootstrap v1.0
