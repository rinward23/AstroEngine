# Fixtures

This directory stores golden datasets used by the cookbook notebooks and API examples.
Every file is derived from deterministic executions of AstroEngine pipelines using the
Swiss Ephemeris stub located at `datasets/swisseph_stub`.

| File | Description | Source |
| ---- | ----------- | ------ |
| `birth_events.csv` | Sample anonymised SolarFire exports used throughout the notebooks. | Generated via `scripts/exec_notebooks.py --refresh-fixtures` |
| `positions_subject.json`, `positions_partner.json` | Natal chart longitudes for the sample events. | `astroengine.chart.natal.compute_natal_chart` |
| `composite_midpoints.json` | Midpoint composite longitudes. | `astroengine.core.rel_plus.composite.composite_midpoint_positions` |
| `davison_positions.json` | Davison chart positions at the time midpoint. | `astroengine.core.rel_plus.composite.davison_positions` |
| `synastry_hits.json` | Directional hits computed with `astroengine.synastry.compute_synastry`. | Notebook 03 |
| `interpretations.json` | Findings derived from the `basic.yaml` rulepack. | Notebook 05 |
| `report_markdown.txt` | Rendered markdown section used in report generation. | Notebook 06 |
| `report_bundle.pdf` | Binary PDF output from Notebook 07. | Notebook 07 |
| `timeline_events.json` | Transit hits for the timeline visualisation. | Notebook 08 |
| `caching_metrics.json` | Serialized cache timing metrics for Notebook 09. | Notebook 09 |
| `checksums.json` | SHA-256 hashes for traceability. | `scripts/exec_notebooks.py` |

Use `python docs-site/scripts/exec_notebooks.py --refresh-fixtures` to rebuild the fixtures.
