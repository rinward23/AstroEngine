# Report Builder (SPEC-B-007)

The Report Builder converts findings into shareable documents. Analysts stitch together
synastry scores, composites, and timelines into Markdown, PDF, or DOCX bundles.

## Layouts

* **Executive summary** — Synastry hit counts, top interpretations, and composite highlights.
* **Timeline** — Transit and return events visualised as bars (see Notebook 08).
* **Appendix** — Raw aspect grids, midpoints, and caching diagnostics for reproducibility.

## Data Sources

| Section | Source |
| ------- | ------ |
| Synastry summary | `/relationship/synastry` response + rulepack findings |
| Composite cards | `/relationship/composite` + `/relationship/davison` |
| Timeline | `/v1/scan/transits` + `/v1/scan/returns` |

## Export

1. Markdown is rendered using the templates in `astroengine/narrative/templates`.
2. PDF/DOCX export calls the same pipeline shown in [`cookbook/07_pdf_export.ipynb`](../cookbook/07_pdf_export.ipynb).
3. Outputs are tagged with the checksum from the cookbook to detect drift.
