# Deploy Runbook

The documentation portal is deployed with [`mike`](https://github.com/jimporter/mike) and GitHub
Pages. The CI workflow ensures notebooks execute cleanly before publishing.

## GitHub Actions

| Job | Description |
| --- | ----------- |
| `docs-build` | Installs `docs-site/requirements.txt`, runs `scripts/exec_notebooks.py --refresh-fixtures`, and builds MkDocs. |
| `docs-deploy` | On `main`, runs `mike deploy <version>` and pushes to `gh-pages`. |
| `link-check` | Validates external/internal links. |

## Local Steps

```bash
python docs-site/scripts/build_openapi.py
python docs-site/scripts/exec_notebooks.py --refresh-fixtures
cd docs-site
mike deploy v0.1
mike alias v0.1 latest
```

Publish via `git push origin gh-pages`.
