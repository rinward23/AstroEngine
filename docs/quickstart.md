# AstroEngine Quickstart

This guide walks through preparing a clean environment, verifying that
Swiss Ephemeris data can be queried, and running the baseline transit
scan used by the recipe docs. Every command below is designed to be
copy-pasteable on macOS, Linux, or WSL.

> **Windows installer:** Operators who used the one-click Setup wizard
> can skip straight to the health checks after reviewing the
> [Windows Installer Support Runbook](runbook/windows_installer_support.md)
> for log locations and repair options.

## 1. Create an isolated environment

AstroEngine targets **Python 3.11**. Start from an empty folder and
install the runtime plus the Swiss Ephemeris bindings:

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -e .[fallback-ephemeris]
```

The `fallback-ephemeris` extra ensures the PyMeeus fallback is available
if you have not yet licensed the Swiss data files.

## 2. Point to Swiss ephemeris files

If you have the official Swiss ephemeris, copy the `*.se1` files into a
folder and expose it through ``SE_EPHE_PATH`` (or ``SWE_EPH_PATH``):

```bash
export SE_EPHE_PATH="$HOME/.sweph/ephe"
```

On Windows PowerShell use ``$env:SE_EPHE_PATH = 'C:/sweph'``.

> Tip: Swiss files are optional during development. When the files are
> absent AstroEngine falls back to PyMeeus so the recipes still produce
> real positions derived from analytic series.

## 3. Run the maintainer health check

Before diving into scans run the maintainer diagnostic. It validates the
Python version, imports the key modules, and confirms that ``swisseph``
or the PyMeeus fallback is usable.

```bash
python -m astroengine.maint --full --strict
```

You should see a summary ending with ``all checks passed``. Resolve any
missing dependency notes before proceeding.

## 4. List detected providers

The CLI exposes a quick environment probe. When ``swisseph`` is
available the command below should report the ``swiss`` provider (and
optionally ``skyfield`` if you have local JPL kernels):

```bash
python -m astroengine env
```

The output lists each registered provider and the module that
registered it. If the list is empty double-check the installation step
above and confirm that ``pip show pyswisseph`` succeeds inside the
virtual environment.

## 5. Produce a baseline transit file

Use the ``transits`` sub-command to generate an actual transit report.
This example scans the Moon–Sun cycle for the first week of 2024 and
stores the output in ``moon_sun_transits.json``.

```bash
python -m astroengine transits \
  --start 2024-01-01T00:00:00Z \
  --end 2024-01-07T00:00:00Z \
  --moving moon \
  --target sun \
  --provider swiss \
  --step 180 \
  --json moon_sun_transits.json
```

Inspect the JSON file to confirm that each event contains ``kind``,
``orb_abs``, ``score``, and provenance metadata. The values are computed
from the real ephemeris queried in step 4.

## 6. Launch the Streamlit scanner (optional)

For a graphical overview install the UI extras, then start the minimal
app:

```bash
pip install -e .[ui]
streamlit run apps/streamlit_transit_scanner.py
```

> **Tip:** a ``streamlit/`` testing shim exists for unit exercises. Launch UI
> scripts with ``streamlit run`` rather than invoking them with ``python`` so the
> real Streamlit package is imported first.

If you installed AstroEngine with the ``streamlit`` extra you can also launch
the Aspect Search dashboard directly:

```bash
pip install "astroengine[streamlit]"
astroengine-streamlit
```

The sidebar echoes the detected providers, Swiss ephemeris path, and the
scan entrypoints that will be attempted. Use the **Run scan** button to
produce the same events as the CLI example above.

## 7. Reproduce the recipes

With the environment validated you can now work through the
step-by-step examples in ``docs/recipes/``:

1. [Daily planner](recipes/daily_planner.md)
2. [Electional window sweep](recipes/electional_window.md)
3. [Transit-to-progressed synastry](recipes/transit_to_progressed_synastry.md)

Each recipe introduces one additional module (profiles, progressions,
fast scans) so a new user can build confidence without needing informal
help.

## 8. Generate the sample PDF report

The reporting pipeline ships with an executable helper that renders a
real natal chart summary into ``generated/reports/sample_chart_report.pdf``.
Run the script after installing the ``reports`` dependencies to
reproduce the artifact without committing binary files:

```bash
pip install -e .[reports]
pip install pyswisseph
python scripts/generate_sample_pdf.py
```

The chart data comes from a real June 1987 birth moment in San
Francisco. The resulting PDF uses the same rendering code exercised by
the API endpoint and includes the default legal disclaimers defined in
``config.yaml``. If ``pyswisseph`` is unavailable the helper exits with a
clear message so the generated artifact is always derived from genuine
ephemeris data.
