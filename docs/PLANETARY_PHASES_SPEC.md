<!-- >>> AUTO-GEN BEGIN: Planetary Phases v1.0 (instructions) -->
Scope
- Define **Morning/Evening star** states and **heliacal rising/setting** for Mercury and Venus (extend to others later). Use simplified elongation and altitude criteria with profile-tunable thresholds.

Definitions
- Morning Star: planet **west** of the Sun (rises before Sun). Evening Star: **east** of the Sun. Determine via ecliptic or apparent elongation sign.
- Heliacal Rising: first visible rising after conjunction with the Sun; Heliacal Setting: last visible setting before conjunction.

Thresholds (defaults, profile-tunable)
- Minimum elongation for visibility: Mercury 12°, Venus 10°. Minimum altitude at civil twilight: ≥ 5°. Ignore atmospheric extinction by default.

Gating
- Add **phase flags** to events; allow severity multipliers (+5–10%) when a transit occurs while a planet is in Morning/Evening or around heliacal events (±3 days).

Outputs
- `phase: morning|evening`, `heliacal_event: rise|set|none`, timestamps if applicable, thresholds used.

Acceptance
- Sample windows match known phase transitions within 1–2 days using the simplified model.
<!-- >>> AUTO-GEN END: Planetary Phases v1.0 (instructions) -->
