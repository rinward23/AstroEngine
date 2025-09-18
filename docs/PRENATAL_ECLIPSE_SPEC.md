<!-- >>> AUTO-GEN BEGIN: Prenatal Eclipses v1.0 (instructions) -->
Scope
- For each natal record, compute the nearest **preceding** (and optionally nearest following) solar and lunar eclipses (the "prenatal eclipse"). Store the exact time, degree, and Saros info if available.

Triggers
- Transit-to-natal checks against the **prenatal eclipse degree** (and its opposite) with tight orbs (≤1°; ≤2° to angles).

Gating
- Enable when `eclipses.prenatal.enabled = true` (default true). Always include transits to prenatal eclipse degree by outer planets; boost if to luminaries/angles.

Outputs
- `prenatal_eclipse`: {kind, exact_iso, degree, saros?}; event fields note `trigger = prenatal_eclipse`.

Acceptance
- Example natal dates reproduce published prenatal eclipses within minutes; transits at exact degree are detected.
<!-- >>> AUTO-GEN END: Prenatal Eclipses v1.0 (instructions) -->
