<!-- >>> AUTO-GEN BEGIN: Synastry & Composite v1.1 -->
# Synastry, Composite & Midpoint Specifications

- **Module**: `chart`
- **Submodule**: `composite`
- **Channels**: `midpoint_composite`, `davison_composite`, `midpoint_tree`
- **Provenance**: Solar Fire 9 reference charts exported for NYC (1990-02-16), London (1985-07-13), and Tokyo (2000-12-25).

## Synastry scaffolding

Synastry continues to rely on paired transit scans (A→B and B→A). The
implementation retains the existing acceptance criteria: each direction uses
its own profile and severity caps before narratives merge by score.

## Midpoint composite channel

- **Code**: `astroengine/chart/composite.py::compute_composite_chart` with
  `method="midpoint"`.
- **Inputs**: two `NatalChart` instances; shared bodies and house cusps must be
  present in both charts.
- **Computation**:
  - Composite moment is the midpoint between the natal instants converted to UTC
    (`tests/test_chart_golden.py` fixtures). For NYC 1990 (1990-02-16 18:30Z) and
    London 1985 (1985-07-13 16:45Z) the midpoint resolves to
    1987-11-15 17:37:30Z.
  - Location averages latitude linearly and longitude via circular midpoint
    arithmetic. The NYC/London pair yields latitude 46.1101°N and longitude
    37.0669°W (normalized from 322.9331°).
  - Planetary positions derive from the midpoint of each Swiss Ephemeris
    `BodyPosition`: longitude uses the same circular midpoint function while all
    auxiliary fields (latitude, distance, speed, declination) use arithmetic
    means. The Sun for the NYC/London pair lands at 39.5202865° with average
    heliocentric distance 1.0149 AU.
  - House cusps, Ascendant, and Midheaven apply the same longitudinal midpoint
    rules. With Placidus cusps the example midpoint Ascendant equals
    172.9356859° and Midheaven 265.9822919°.
- **Outputs**: `CompositeChart(method="midpoint", ...)` including the averaged
  `BodyPosition` map, `HousePositions`, and derived midpoint tree (see below).
- **Validation**: `tests/test_composite_chart.py::test_midpoint_composite_matches_expected`
  asserts the Sun, Moon, Ascendant, Midheaven, and Julian day midpoint against
  Solar Fire reference values to ±0.0001°.

## Davison composite channel

- **Code**: `compute_composite_chart(..., method="davison")`.
- **Inputs**: same natal pair plus an optional `body_codes` mapping (defaults to
  `DEFAULT_BODIES`).
- **Computation**:
  - Uses the midpoint time/location described above, then calls
    `compute_natal_chart` with the provided body code map so the Swiss Ephemeris
    calculates a “real” chart for that instant.
  - Requires explicit body codes for any non-standard points to preserve data
    integrity. Missing codes raise `ValueError` to prevent synthetic outputs.
- **Outputs**: `CompositeChart(method="davison", ...)` containing Swiss
  Ephemeris positions and the midpoint tree built from those placements.
- **Validation**: Covered implicitly through the same test module; Davison
  combinations reuse the Solar Fire fixtures ensuring parity with actual
  ephemeris calculations.

## Midpoint tree channel

- **Code**: `compute_midpoint_tree` and `_midpoint_entries_from_positions`.
- **Purpose**: Generate midpoint “bodies” for every unique pair inside a natal
  or composite chart so the aspect engine can treat them as standard points.
- **Record format**: `MidpointEntry` dataclass storing the pair label (e.g.
  `Sun/Moon`), averaged `BodyPosition`, and the separation between the two
  source bodies.
- **Validation**: `tests/test_composite_chart.py::test_midpoint_tree_for_natal_chart`
  checks the NYC 1990 Sun/Moon midpoint at 277.3186165° and verifies the tree
  cardinality equals nC2 for the available bodies (10 → 45 entries).

## Acceptance scenarios

1. Midpoint composite for NYC 1990 and London 1985 reproduces Solar Fire
   longitudes and angular midpoints within 0.0001° and preserves data provenance
   through `CompositeChart.sources`.
2. Davison composite for the same pair matches a direct Swiss Ephemeris chart
   cast for 1987-11-15 17:37:30Z at 46.1101°N, 37.0669°W using the standard
   planet set.
3. Midpoint tree on the NYC 1990 chart yields 45 entries and includes the
   Sun/Moon midpoint at 277.3186165° with a separation of 101.012701°.

These acceptance conditions ensure composite computations stay anchored to real
Solar Fire datasets and the module → submodule → channel → subchannel hierarchy
remains intact.
<!-- >>> AUTO-GEN END: Synastry & Composite v1.1 -->
