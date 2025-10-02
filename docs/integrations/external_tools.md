# External tool integrations

AstroEngine keeps a registry of third-party tools that feed SolarFire-derived
workflows.  Each entry is backed by an upstream project that publishes
deterministic ephemeris or chart data.

## Ephemeris libraries

- **Swiss Ephemeris (`sweph` / `pyswisseph`)** – the core Swiss ephemeris C
  library is available from AstroDienst and ships with the Swiss Ephemeris
  Public License.  The Python bindings exposed on PyPI (`pyswisseph`) provide
  access to the same algorithms and load the canonical ephemeris files shipped
  in `datasets/swisseph_stub`.  See <https://www.astro.com/swisseph/> and
  <https://pypi.org/project/pyswisseph/> for installation instructions.
- **Skyfield + JPL kernels** – Skyfield queries the official DE ephemerides and
  relies on the `jplephem` package for compressed kernel access.  The
  `astroengine.providers.skyfield_kernels` helper documents the DE440s cache
  folder used by the runtime.  See <https://rhodesmill.org/skyfield/> and
  <https://pypi.org/project/jplephem/>.

## Python toolkits

- **Flatlib** – classical astrology calculations implemented in pure Python,
  referenced by AstroEngine for delineations that complement Swiss Ephemeris
  and Skyfield data.  Repository: <https://github.com/flatangle/flatlib>.

## Desktop workflows

- **Maitreya 8** – open-source Vedic astrology suite distributed via
  SourceForge.  Export chart or transit reports from the application and index
  the resulting CSV/XML files alongside SolarFire datasets before running
  AstroEngine importers.  Project page: <https://sourceforge.net/projects/maitreya/>.
- **Jagannatha Hora (JHora)** – Windows desktop program released by P. V. R.
  Narasimha Rao.  Use its export utilities to generate deterministic transit
  tables that can be referenced by AstroEngine rulesets.  Project page:
  <https://www.vedicastrologer.org/jh/>.
- **Open source Panchanga (panchangam)** – Python almanac generator maintained
  at <https://github.com/karthikraman/panchangam>.  Its calculated tithi and
  nakshatra tables can be indexed in the module registry for downstream
  ingestion.

The registry entries created in `astroengine.modules.integrations` ensure these
sources remain discoverable without removing existing modules or datasets.
