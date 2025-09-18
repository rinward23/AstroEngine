<!-- >>> AUTO-GEN BEGIN: Galactic Points v1.0 (instructions) -->
Scope
- Include **Galactic Center (GC)** and **Anti-Center**, and **Supergalactic Center (SGC)** and Anti-SGC as fixed reference points.

Computation
- Store RA/Dec (J2000) for GC and SGC (with provenance). Convert to ecliptic longitude for **date** using precession model; expose longitudes via provider utility.

Orbs & Gating
- Default orbs: GC/SGC conjunctions ≤ 1° (≤ 2° to angles). Include only when contacted by transiting outer planets or when the natal point is an angle/luminary.

Outputs
- `fixed_point: GC|Anti-GC|SGC|Anti-SGC`, method metadata, aspect info.

Acceptance
- Longitudes match reputable references within a small tolerance (≤ 0.1°) after precession.
<!-- >>> AUTO-GEN END: Galactic Points v1.0 (instructions) -->
