# Recipes Overview

The examples in this section walk through end-to-end workflows that new
users can reproduce with real data. Each recipe builds on the previous
one, so complete them in order unless you are already familiar with the
modules involved.

1. [Daily planner](daily_planner.md) — combines natal positions with
   hourly transit samples to produce a planner-style table.
2. [Electional window sweep](electional_window.md) — searches for narrow
   aspect windows using the fast scan helper.
3. [Transit-to-progressed synastry](transit_to_progressed_synastry.md) —
   fuses secondary progressions with live transits for relationship or
   event analysis.
4. [Narrative profiles and time-lords](narrative_profiles.md) — configure
   sidereal ayanāṁśas, electional narratives, and active timelord stacks.
5. [Locational maps and outer-cycle timelines](locational_timelines.md) —
   emit astrocartography linework, local space vectors, and outer planet
   windows for dashboards.

Every script uses Swiss Ephemeris data (or the documented PyMeeus
fallback) and references profiles stored in this repository. No synthetic
values are introduced; if a data dependency is missing, the script raises
an error instead of guessing.
