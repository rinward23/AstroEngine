# >>> AUTO-GEN BEGIN: Merge Strategy Guide v1.0

## Quick rules

1. Rebase your feature branch on `origin/main` *before* you push or open a PR.
2. If you see conflict blocks, keep only the code you want and delete the markers.
3. Use built-ins if you want one side entirely:

   * Keep ours: `git checkout --ours path/to/file`
   * Keep theirs: `git checkout --theirs path/to/file`
   * Then `git add` + `git commit`.
4. Train Git to remember: `git config --global rerere.enabled true`.

## Standard flow (developer)

```bash
git fetch origin
git rebase --rebase-merges origin/main
# resolve if asked, run tests
make lint
# push safely
git push --force-with-lease
```

## When conflicts keep returning

* Prefer smaller PRs; rebase daily.
* Avoid editing generated files by hand.
* If two branches touch the same function, agree on one branch to land first; rebase the other.

## FAQ

**Q: I want “theirs” version for a file.**

```bash
git checkout --theirs path/to/file && git add path/to/file && git commit
```

**Q: My push is blocked by the hook.** It means you’re behind or have markers. Rebase and/or clean markers, then push.

# >>> AUTO-GEN END: Merge Strategy Guide v1.0
