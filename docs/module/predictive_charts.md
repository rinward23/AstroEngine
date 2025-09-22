# Predictive Charts Module

The predictive module organises timing and derived chart techniques under
the shared module → submodule → channel → subchannel hierarchy. All data
is sourced from Swiss Ephemeris calculations; no synthetic coordinates are
emitted.

## Submodules

### `progressions`

Secondary progressions are produced at an annual cadence (day-for-a-year
mapping) and expose longitude samples for the standard `DEFAULT_BODIES`
set. Helper APIs:

- `astroengine.detectors.progressions.secondary_progressions`
- `astroengine.chart.progressions.compute_secondary_progressed_chart`

### `directions`

Solar arc directions use the progressed Sun motion to arc the natal
positions of configured bodies. The detector helper returns annual
samples; the chart helper applies the arc to the natal chart structure.

- `astroengine.detectors.directions.solar_arc_directions`
- `astroengine.chart.directions.compute_solar_arc_chart`

### `returns`

Solar and lunar returns locate the exact instant when the Sun or Moon
matches its natal longitude. The detector operates on Julian day windows,
while `astroengine.chart.returns.compute_return_chart` builds a fully
scored chart at the return moment for a supplied location.

### `derived_charts`

Derived overlays currently include harmonic charts (multiplying natal
longitudes by an integer factor) and midpoint composites (averaging two
charts). Both utilities expose dataclasses capturing the provenance of the
derived positions.

- `astroengine.chart.harmonics.compute_harmonic_chart`
- `astroengine.chart.midpoints.compute_composite_chart`
