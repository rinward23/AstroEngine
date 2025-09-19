# Event Detector Channels Index

Channel documentation ensures every runtime channel/subchannel remains discoverable.

| Channel | Subchannel(s) | Description | Data provenance |
| ------- | ------------- | ----------- | --------------- |
| `direct` | — | Direct station detections for planets | Solar Fire `STATIONS.RPT`, Swiss Ephemeris speed samples |
| `shadow` | `pre`, `post` | Station shadow periods | Solar Fire retrograde shadow tables |
| `sign` | — | Zodiac sign ingresses | Solar Fire ingress exports |
| `house` | — | House ingresses for relocation and mundane use cases | Atlas/TZ dataset, Solar Fire house ingress logs |
| `solar` | `lunation`, `eclipse` | Solar lunations/eclipses | NASA GSFC Besselian elements |
| `lunar` | `lunation`, `eclipse` | Lunar lunations/eclipses | NASA Five Millennium Canon |
| `oob` | — | Declination out-of-bounds | Swiss Ephemeris declination data |
| `parallel` | `contra` | Declination parallels and contra-parallels | FK6 declination aspects |
| `composite` | — | Midpoint activations for composite charts | Solar Fire midpoint exports |
| `synastry` | — | Midpoint activations for synastry | Solar Fire synastry module |
| `bright_list_v1` | — | Fixed star contacts | `resources/fk6_bright_stars.csv` |
| `angles` | — | Vertex/anti-vertex contacts | Atlas/TZ dataset |
| `secondary` | — | Secondary progressions | Solar Fire progression tables |
| `primary` | — | Primary directions | Traditional sources, Solar Fire primary direction module |
| `astrocartography` | `meridian`, `horizon`, `parans` | Relocation/astrocartography lines | Solar Fire astrocartography exports |

Changes must add rows; do not remove existing channels without governance approval.
