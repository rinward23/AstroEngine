# Feature Flags Reference

```AUTO-GEN[profiles.feature_flags]
OVERVIEW
  - Document default feature toggles and configuration knobs referenced by rulesets and providers. Values align with `profiles/base_profile.yaml` and must remain schema-compatible.

TABLE OF FLAGS

| Flag Path | Type | Default | Description |
|-----------|------|---------|-------------|
| `stations.enabled` | bool | true | Enable transit station detection for configured bodies. |
| `stations.outer_always_on` | bool | false | Always include outer-planet stations regardless of natal proximity. |
| `stations.natal_gate_orb_deg` | float | 2.0 | Orb threshold (degrees) for including conditional stations. |
| `ingresses.enabled` | bool | true | Emit sign ingress events. |
| `ingresses.include_moon` | bool | false | Require explicit opt-in for Moon ingresses. |
| `ingresses.inner_mode` | enum | `angles_only` | Options: `always`, `angles_only`. Controls Mercury/Venus ingestion gates. |
| `lunations.enabled` | bool | true | Emit lunations and baseline severity scores. |
| `lunations.oob_bonus` | bool | true | Apply out-of-bounds severity bonus when Moon exceeds declination threshold. |
| `eclipses.enabled` | bool | true | Allow eclipse tagging when orb criteria met. |
| `eclipses.max_orb_deg` | float | 1.0 | Maximum separation between eclipse degree and natal/angle for inclusion. |
| `declination_aspects.enabled` | bool | true | Detect parallels/contraparallels. |
| `declination_aspects.parallels` | bool | true | Emit parallel declination events. |
| `declination_aspects.contraparallels` | bool | true | Emit contraparallel declination events. |
| `out_of_bounds.enabled` | bool | true | Track out-of-bounds entries/exits. |
| `out_of_bounds.threshold_deg` | float | 23.45 | Declination threshold for out-of-bounds flagging. |
| `antiscia.enabled` | bool | false | Enable antiscia/contra-antiscia detection. |
| `midpoints.enabled` | bool | true | Enable midpoint detection. |
| `midpoints.base_pairs` | list[str] | `[sun_moon, asc_mc, mc_node]` | Core midpoint pairs using Cosmobiology conventions. |
| `fixed_stars.enabled` | bool | false | Emit fixed-star conjunction events. |
| `fixed_stars.lunation_bonus` | bool | false | Apply severity bonus for lunations on bright stars. |
| `profections.enabled` | bool | true | Generate annual profection timelines. |
| `profections.cycle` | enum | `annual` | Supported: `annual`, `monthly` (future). |
| `returns.enabled` | bool | true | Compute return events (solar/lunar). |
| `returns.solar` | bool | true | Enable solar return detection. |
| `returns.lunar` | bool | true | Enable lunar return detection. |
| `returns.lunation_boost` | bool | true | Apply severity boost to lunations near returns. |
| `progressions.enabled` | bool | false | Gate secondary progressions module. |
| `timelords.enabled` | bool | false | Gate zodiacal releasing / Firdaria modules. |
| `maps.enabled` | bool | false | Enable astrocartography/local space modules. |
| `draconic.enabled` | bool | false | Enable draconic zodiac conversions. |
| `sidereal.enabled` | bool | false | Toggle sidereal zodiac handling. |
| `sidereal.ayanamsha` | enum | `lahiri` | Default ayanamsha when sidereal enabled. |
| `house_system.default` | enum | `whole_sign` | Default house system. |
| `house_system.available` | list[str] | see table | Supported house systems. |
| `minor_planets.enabled` | bool | false | Enable Ceres/Pallas/Juno/Vesta as transit bodies. |
| `minor_planets.stations` | bool | false | Allow minor-planet station detection. |
| `minor_planets.ingresses` | bool | false | Allow minor-planet sign ingress detection. |
| `dwarfs.enabled` | bool | false | Enable Eris/Sedna. |
| `providers.skyfield.cache_path` | str | `${ASTROENGINE_CACHE}/skyfield/de440s` | Override cache directory. |
| `providers.swe.enabled` | bool | false | Enable Swiss Ephemeris provider. |
| `providers.swe.delta_t` | float | null | Override delta-T model when using SWE. |

VALIDATION
  - Profile loader must ensure boolean defaults evaluate correctly, enumerations match documented options, and list-valued flags only contain supported entries.
  - Schema upgrades must retain backward compatibility by mapping deprecated flags or logging migrations.
```
