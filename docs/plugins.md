# Plugin Architecture

AstroEngine is designed to accept external modules without breaking the
module → submodule → channel → subchannel layout. Three plugin surfaces are
stable today: ephemeris providers, scan entrypoints, and detector/scoring
hooks exposed through ``astroengine.plugins``.

## Ephemeris providers

``astroengine.providers`` exposes a lightweight registry keyed by provider
name. Each provider implements the ``EphemerisProvider`` protocol:

```python
class EphemerisProvider(Protocol):
    def positions_ecliptic(self, iso_utc: str, bodies: Iterable[str]) -> Dict[str, Dict[str, float]]: ...
    def position(self, body: str, ts_utc: str) -> BodyPosition: ...
```

Register your provider during import:

```python
from astroengine.providers import register_provider

class MyProvider:
    ...

register_provider("my_provider", MyProvider())
```

The built-in Swiss and Skyfield providers follow this pattern. Keep the
registration side-effect inside the provider module so importing it is
enough to make the provider available.

### Provenance expectations

Providers must document:

- The data source (Swiss ephemeris path, JPL kernel checksum, Solar Fire
  export hash).
- Supported bodies and coordinate frames.
- Any caching layers or analytical approximations used when raw data is
  unavailable.

Add the documentation to ``docs/providers`` or link to an external design
note. When a provider cannot return a value (missing kernel, bad ephemeris
path) raise a descriptive exception—never fabricate positions.

### Testing a provider

After registering a provider, run the quick provider listing to confirm
it appears in the registry:

```bash
python -m astroengine env
```

Then run a short scan that references the provider explicitly:

```bash
python -m astroengine transits --start 2024-01-01T00:00:00Z \
  --end 2024-01-02T00:00:00Z --moving sun --target moon --provider my_provider
```

The command must succeed and produce real transits derived from the data
source documented above.

## Detector and scoring hooks

``astroengine.plugins`` exposes a Pluggy manager. Third-party packages can
register detectors, scoring extensions, and lightweight UI panels by
implementing the hook specifications defined in
``astroengine.plugins.HookSpecs``. A detector registration looks like:

```python
from astroengine.plugins import hookimpl


class MyPlugin:
    ASTROENGINE_PLUGIN_API = "1.0"

    @hookimpl
    def register_detectors(self, registry):
        registry.register("my.detector", my_detector_fn)

    @hookimpl
    def extend_scoring(self, registry):
        registry.register("my.score", my_extension_fn, namespace="custom")
```

Callables receive typed contexts and may emit metadata describing the source
of their calculations. The plugin API is versioned so upgrades of
AstroEngine can flag incompatible packages early.

Runtime inspection is available from the CLI:

```bash
astroengine plugins --entrypoints --detectors --score-extensions
```

The command prints loaded entry points, detector names, score extension
namespaces, and UI panels. ``--json`` produces a machine-readable summary.

## User plugin sandboxing

AstroEngine loads user-supplied aspect and lot definitions from the
``ASTROENGINE_PLUGIN_DIR`` directory (``~/.astroengine/plugins`` by default).
Each ``.py`` file is parsed before execution to enforce a conservative
import allow list: standard-library modules and the public ``astroengine``
package hierarchy are permitted, while third-party imports are rejected.
Disallowed imports or runtime errors are recorded and exposed through
``astroengine.plugins.registry.get_user_plugin_errors()`` so callers and the
Streamlit settings panel can surface a warning banner. Plugins that fail to
load are skipped and remain inactive until their issues are corrected.

## Scan entrypoints

Graphical clients such as ``apps/streamlit_transit_scanner.py`` discover
scan functions dynamically. The helper
``astroengine.app_api.available_scan_entrypoints`` searches three places:

1. Explicit entrypoints passed to ``run_scan_or_raise``.
2. The ``ASTROENGINE_SCAN_ENTRYPOINTS`` environment variable.
3. Built-in fallbacks such as ``astroengine.engine.scan_contacts``.

To expose a custom scan function, ensure it accepts ``start_utc``,
``end_utc``, ``moving``, ``targets``, and ``provider`` keyword arguments
(or their documented aliases). Set the environment variable before
launching the Streamlit app to test the discovery flow:

```bash
export ASTROENGINE_SCAN_ENTRYPOINTS="my_module:custom_scan"
streamlit run apps/streamlit_transit_scanner.py
```

The sidebar will list your function once it imports successfully. Return
a sequence of event-like objects (dicts, dataclasses, or canonical
``TransitEvent`` instances) so ``run_scan_or_raise`` can normalize the
output for exporters.

## Packaging guidance

When distributing plugins:

- Keep them in separate packages so upgrades do not risk deleting core
  modules.
- Depend on the published AstroEngine API surface (``astroengine.core``
  and ``astroengine.providers``) rather than private modules.
- Ship documentation describing required data files and checksums, and
  reference the instructions in this repository so users can reproduce
  your environment.

Following these guidelines ensures the plugin ecosystem stays compatible
while protecting the integrity of the data pipeline.
