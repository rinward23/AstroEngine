# Relationship report export (B-014)

The relationship export endpoints assemble interpretation findings, scores,
and optional figures into a styled PDF or DOCX document. They extend the
B-007 relationship narratives without introducing synthetic content: every
paragraph, table cell, and figure must come from your recorded findings or
figure payloads.

## PDF export

`POST /v1/report/relationship/pdf`

```json
{
  "findings": [{"title": "Sun harmonises Moon", "text": "…"}],
  "meta": {
    "title": "Aurora × Vega", "generated_at": "2024-01-10T12:00:00Z"
  },
  "theme": "default",
  "figures": {
    "tables": [{"id": "grid", "title": "Aspect Grid", "headers": ["Body", "Aspect"],
                  "rows": [["Sun", "Trine Moon"]]}]
  },
  "include_toc": true,
  "include_appendix": true,
  "paper": "A4",
  "scores": {"harmony": 8.5, "tension": {"Mars-Venus": 3.1}}
}
```

The service renders Markdown → HTML → PDF through headless Chromium when
available, falling back to WeasyPrint or a deterministic placeholder page
if neither renderer can be loaded. Metadata (`/Info` keys) is embedded from
`meta` so downstream archives can search titles, authors, and keywords.

## DOCX export

`POST /v1/report/relationship/docx`

If Pandoc is installed, the Markdown is converted through `pypandoc`. When
Pandoc is missing the service uses `python-docx`, preserving headings,
paragraphs, and lists. Document core properties mirror the PDF metadata.

## Themes and CSS

The built-in themes are `default`, `dark`, and `print`. A custom CSS file
may be supplied by URL (`custom_theme_url`); the service downloads the
stylesheet (≤ 256 KB) and appends it to the theme bundle.

## Data integrity

All tables, figures, and findings must be derived from actual observations
or calculations. The exporter never fabricates values; if required payloads
are missing, prefer omitting the section or signalling the absence in the
document body.
