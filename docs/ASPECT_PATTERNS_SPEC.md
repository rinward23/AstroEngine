<!-- >>> AUTO-GEN BEGIN: Aspect Patterns v1.0 (instructions) -->
Scope
- Define and detect classic multi-leg patterns using existing aspect detections: Grand Trine, Kite, T-Square, Grand Cross, Mystic Rectangle, Yod, Thor's Hammer (Fist of God), Grand Sextile (Star of David), Grand Quintile/Septile/Novile (when harmonics enabled).

General Rules
- A pattern is present when **all required legs** exist within their **allowed orbs**, and the polygon **closes** within a small angular tolerance (closure_tol ≤ 2° by default).
- Use the engine's orb policy for each leg; optionally apply a **pattern orb factor** (e.g., 0.9×) for tighter coherence.
- Participants may be transiting→natal, natal↔natal (for natal pattern reference), or transit-only (rare; context timelines). Start with transiting body to natal points.

Definitions (legs)
- Grand Trine: 3 nodes linked by 3 × 120°.
- Kite: Grand Trine + an **opposition** to one node; include the two **sextiles** to the opposing apex.
- T-Square: 1 **opposition** with 2 **squares** to a third apex.
- Grand Cross: 2 **oppositions** forming a cross, with 4 **squares** closing the loop.
- Mystic Rectangle: 2 **oppositions** + 4 **sextiles** forming a rectangle.
- Yod: 2 **quincunxes** to an apex + base **sextile** between the other two points.
- Thor's Hammer: apex receives 2 **sesquisquares** (135°) with a **semisquare** (45°) between the base.
- Grand Sextile: 6 points alternating **sextiles** and **trines** (rare; allow inset variants).
- Grand *Harmonic* (5/7/9/11): 5/7/9/11 nodes linked by the respective harmonic aspects when H5/H7/H9/H11 are enabled.

Scoring & Gating
- **Pattern severity** = weighted mean of leg severities × **coherence factor** (1.0 at perfect closure; decays with closure error).
- Gate when (a) all legs within orb, (b) coherence ≥ 0.8, and (c) at least one **outer planet** participates or a **natal angle** is a node. Partile on any leg auto-passes.

Outputs
- Emit a composite event carrying: pattern_name, nodes (ordered), legs (list of {body/point A, aspect, body/point B, orb}), apex (if defined), coherence, severity.

Acceptance
- Synthetic examples for each pattern pass; removing any leg breaks detection; tightening orbs increases coherence.
<!-- >>> AUTO-GEN END: Aspect Patterns v1.0 (instructions) -->
