# Profile Override Precedence

AstroEngine composes runtime profiles from multiple layers so that site-wide
settings remain immutable while individual users can tailor severity and orb
policies.

1. **Base layer** – `profiles/base_profile.yaml` defines the canonical values
   for orb policies, severity modifiers, and feature flags. These values are
   sourced from Solar Fire exports and should only change when the primary
   dataset is revised.
2. **User overrides** – `profiles/user_overrides.yaml` may contain keyed
   entries under `users`. When `load_profile(profile_id, user="<id>")` is
   invoked the matching block is deep-merged on top of the base layer. This is
   the correct place to adjust default severity multipliers for a specific
   account without editing the shared profile file.
3. **Runtime overrides** – Callers may supply the ``overrides`` keyword to
   :func:`astroengine.profiles.load_profile`. These mappings apply last and
   override both the base profile and any per-user customisations.

The effective profile published by :func:`load_profile` always includes fully
realised policy payloads:

- `policies.orb` – combined `profiles/orb_policy.json` with any overrides.
- `policies.severity` – merged `profiles/scoring_policy.json` including
  condition modifiers.
- `policies.visibility` – minimum score thresholds from
  `profiles/visibility_policy.json`.

Profile data flows into the execution context via
:func:`astroengine.core.config.profile_into_ctx`, which keeps the precedence
order intact (base → user → runtime). Update this document whenever additional
layers are added so downstream integrators understand how to customise
profiles without losing tracked modules.
