# Quickstart

!!! abstract "Audience"
    This quickstart is built for developers and analysts onboarding to the B‑stack. It
    assumes familiarity with Python 3.11, MkDocs, and AstroEngine's module hierarchy.

1. **Clone & bootstrap**

   ```bash
   git clone https://github.com/example/astroengine.git
   cd astroengine
   uv pip install -r requirements.txt
   uv pip install -r docs-site/requirements.txt
   ```

2. **Fetch Swiss Ephemeris data (local only)**

   The docs use the redistributable stub data under `datasets/swisseph_stub`. To switch to a
   licensed ephemeris, mount it locally and export `SE_EPHE_PATH`.

   ```bash
   export SE_EPHE_PATH=$PWD/datasets/swisseph_stub
   ```

3. **Generate OpenAPI + execute notebooks**

   ```bash
   python docs-site/scripts/build_openapi.py --output docs-site/docs/api/openapi
   python docs-site/scripts/exec_notebooks.py --refresh-fixtures
   ```

   `exec_notebooks.py` runs the nine cookbook notebooks in a clean environment and verifies
   their result checksums against the fixtures in `docs/fixtures`.

4. **Preview the docs**

   ```bash
   cd docs-site
   mkdocs serve
   ```

   Visit <http://localhost:8000>. Search, copy-code buttons, and the light/dark toggle are
   available via the Material theme features.

5. **Deploy a new version**

   ```bash
   mike deploy v0.1
   mike alias v0.1 latest
   git push origin gh-pages
   ```

   The GitHub Actions workflow `docs-deploy.yml` automates these steps for pushes to `main`.

!!! tip "Need a hosted runtime?"
    Click the ![Colab badge](https://img.shields.io/badge/Colab-run%20cookbook-orange)
    or ![VS Code badge](https://img.shields.io/badge/VS%20Code-Dev%20Container-blue) badges
    at the top of each notebook to launch an ephemeral environment preloaded with pinned
    dependencies and fixture datasets.
