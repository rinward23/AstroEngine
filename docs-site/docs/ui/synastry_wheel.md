# Synastry Wheel (SPEC-B-009)

The synastry wheel visualises two natal charts with overlays and aspect grids.

## Components

* **Chart A / Chart B wheels** — Rendered from `positions_subject.json` and `positions_partner.json`.
* **Aspect grid** — Uses the same data structure returned by `/relationship/synastry`.
* **Domain heatmap** — Aggregates `domains` weights from the synastry response.

## Screenshots

![Synastry wheel](../assets/figures/astroengine-logo.svg)

## Troubleshooting

* Ensure the Swiss Ephemeris path is configured; missing ephemeris data yields empty wheels.
* Minor aspect toggles follow `BASE_ASPECTS`; enable them before loading for correct arc counts.
