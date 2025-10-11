# Profiles Guide

AstroEngine keeps configuration for orbs, severity multipliers, feature
flags, and provider preferences in the ``profiles/`` directory. Profiles
are data-only; every value traces back to a Solar Fire export or a
documented calculation so no runtime module loses access to provenance.

## Directory tour

- ``profiles/base_profile.yaml`` — master profile that wires feature
  flags, provider cadences, orb tables, resonance weights, and domain
  scoring defaults.
- ``profiles/feature_flags.md`` — authoritative description of the
  ``flags`` section exposed in the profile.
- ``profiles/aspects_policy.json`` — per-aspect orb allowances used by
  ``astroengine.detectors_aspects``.
- ``profiles/tradition_scoring.json`` — tradition overlays (e.g., Vedic
  drishti angles) used by the scoring engine's tradition helpers.
- ``profiles/vca_outline.json`` — registry map for the Venus Cycle
  Analytics channels.
- ``profiles/dignities.csv`` and ``profiles/fixed_stars.csv`` — static
  datasets referenced by severity scoring and the future fixed-star
  channel.
- ``profiles/dashboard_panes.yaml`` — optional overrides for Streamlit
  portal panes, enabling new renderers or label/category adjustments
  without editing application code.

All files embed ``provenance`` sections or column-level citations so a
change can be traced back to its Solar Fire source.

## Loading a profile in Python

The helpers in :mod:`astroengine.profiles` return strongly-typed views of
the profile data. The snippet below prints the domain resonance weights
and the enabled feature flags from the baseline profile:

```python
from pprint import pprint

from astroengine.profiles import load_base_profile, load_resonance_weights

profile = load_base_profile()
resonance = load_resonance_weights(profile)

print("Resonance weights (normalized):", resonance.as_mapping())
print("Enabled flags:")
pprint({k: v for k, v in profile["flags"].items() if v})
```

Run the script with ``python - <<'PY'`` to verify that the data matches
what is recorded in ``profiles/feature_flags.md``.

## Applying a profile to a scan context

Most engines accept a context dictionary describing which orbs and
feature toggles to apply. Use ``astroengine.core.config.profile_into_ctx``
to merge a profile payload into an existing context:

```python
from astroengine.core.config import profile_into_ctx
from astroengine.profiles import load_base_profile

ctx = {"emit_domains": True}
profile = load_base_profile()
rich_ctx = profile_into_ctx(ctx, profile)
```

``rich_ctx`` now contains ``aspects``, ``orbs``, ``flags``, and domain
profile metadata that downstream scanners consume.

## Customising a profile

Create a small overlay file when experimenting with different orbs or
feature flags. The JSON example below narrows the square orb to two
degrees and enables fixed-star detection:

```json
{
  "id": "lab-tight",
  "flags": {
    "fixed_stars": {"enabled": true}
  },
  "orbs": {
    "override": {
      "aspect_square": 2.0
    }
  }
}
```

Merge the overlay with ``profile_into_ctx`` by loading the JSON and
passing it as the second argument. Keep overlays under version control
and document the Solar Fire source file or analytical justification in
an adjacent ``README`` so the data lineage remains intact.

## Configuring Streamlit portal panes

The main portal assembles its dashboard panes from built-ins, plugin
entry points, and an optional ``profiles/dashboard_panes.(yaml|json)``
file. Each entry binds a renderer import path to a pane identifier,
human-friendly label, and category for the slot selector. Renderers must
be callables that accept a ``streamlit.DeltaGenerator`` instance.

Example ``yaml`` record:

```yaml
- id: astro_map
  label: Astrocartography Map
  category: Geospatial
  renderer: ui.streamlit.panes.catalog:_render_map
```

The same keys apply to JSON. Provide your own callable import path to
add new visuals or regroup existing panes without touching
``ui/streamlit/main_portal.py``.

## Validating changes

Any edit to ``profiles/`` should be accompanied by a ``pytest`` run. The
suite exercises the orb policy, VCA outline, and resonance weights to
ensure schema compatibility. Update
``docs/governance/data_revision_policy.md`` with the source citation for
material changes.
