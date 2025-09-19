# Event Detector Submodules Index

This index preserves the mapping between runtime submodules and their documentation to prevent accidental loss when updating the registry.

| Submodule | Channels | Documentation |
| --------- | -------- | ------------- |
| `stations` | `direct`, `shadow` | Refer to `docs/module/event-detectors/overview.md` (station rows) |
| `ingresses` | `sign`, `house` | Refer to `docs/module/event-detectors/overview.md` |
| `lunations` | `solar`, `lunar` | Refer to `docs/module/event-detectors/overview.md` and `docs/module/providers_and_frames.md` |
| `eclipses` | `solar`, `lunar` | NASA datasets listed in overview provenance |
| `combustion` | `inferior`, `superior` | Orbs policy documented in `docs/module/core-transit-math.md` |
| `declination` | `oob`, `parallel` | Declination rules from overview table |
| `midpoints` | `composite`, `synastry` | Midpoint activations per overview |
| `fixed-stars` | `bright_list_v1` | Data references in `docs/module/data-packs.md` |
| `vertex` | `angles` | Vertex contacts using atlas dataset |
| `progressions` | `secondary` | Refer to overview and Solar Fire progression tables |
| `directions` | `primary` | Traditional sources noted in overview |
| `relocation` | `astrocartography` | Atlas/TZ dataset references in overview |

Future updates must expand this table rather than delete rows, ensuring module/submodule/channel integrity remains auditable.
