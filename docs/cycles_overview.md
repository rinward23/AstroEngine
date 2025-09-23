# Cycles & Astrological Ages Toolkit

AstroEngine now ships with a dedicated cycles namespace covering fixed-star
parans, heliacal phases, outer-planet timelines, and astrological age
analytics. The new modules extend the module → submodule → channel hierarchy
without replacing any existing registries so downstream SolarFire datasets
continue to load without regression.

## Fixed-star parans and heliacal phases

- :func:`astroengine.fixedstars.parans.compute_star_parans` samples the local
  horizon using Skyfield/JPL kernels to flag moments when a fixed star and a
  planet simultaneously occupy ASC/MC/DESC/IC angles. The output contains the
  midpoint timestamp, underlying horizon events, and the absolute separation in
  minutes for downstream dashboards.
- :func:`astroengine.fixedstars.parans.compute_heliacal_phases` scans the
  twilight band either side of sunrise and sunset to estimate heliacal rising
  and setting windows. Visibility is only reported when the Sun remains below a
  configurable altitude threshold so every result traces back to real solar and
  stellar altitude measurements.

Both workflows reference the ``star_names_iau.csv`` dataset shipped with the
repository and require a locally installed Skyfield kernel (``de440s.bsp`` or
compatible).

## Generational cycle dashboards

- :func:`astroengine.cycles.outer_cycle_timeline` evaluates Swiss Ephemeris
  longitudes for Jupiter through Pluto at a regular cadence (default: 30 days)
  and records the signed/angular separation for every planet pair. Aspect tags
  (0°, 45°, 60°, 90°, 120°, 135°, 150°, 180°) are attached when the separation
  falls within a configurable orb so dashboards can highlight conjunctions or
  alignments automatically.
- :func:`astroengine.cycles.neptune_pluto_wave` specialises the timeline for the
  Neptune–Pluto pair and adds a derivative column expressed in degrees per year
  to track wave crests or troughs in mundane research.

All computations flow through :class:`astroengine.ephemeris.SwissEphemerisAdapter`
and therefore inherit the project’s provenance guarantees and caching rules.

## Astrological ages

- :func:`astroengine.cycles.compute_age_series` locates the Sun’s Aries ingress
  for each requested year and records the ayanamsha offset together with the
  sidereal longitude of the tropical vernal point. The active “age” sign is the
  sidereal sign containing the projected point.
- :func:`astroengine.cycles.derive_age_boundaries` collapses the series into
  boundary markers for dashboards. By default the Lahiri ayanamsha is used, but
  any ayanamsha supported by :class:`SwissEphemerisAdapter` may be supplied.

These additions surface under a new ``cycles`` module in the registry so API
consumers can introspect capabilities and datasets alongside the existing VCA
and esoteric metadata.

