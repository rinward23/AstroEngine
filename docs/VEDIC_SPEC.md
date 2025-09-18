<!-- >>> AUTO-GEN BEGIN: Vedic Layer v1.0 (instructions) -->
Scope
- Nakshatras (27), padas (108), Vimshottari dasha timeline, Panchānga (tithi/yoga/karana/vāra) as optional context flags.
- Ayanamsha choice required (default: Lahiri); all sidereal calculations use chosen ayanamsha.

Nakshatras
- Segment: 13°20′ each; padas: 3°20′ each.
- Calculation: sidereal_long = tropical_long − ayanamsha; idx = floor(sidereal_long / 13°20′).
- Output: nakshatra_name, pada (1–4), lord (per Vimshottari), exact bounds (deg), distance_to_center (deg).
- Acceptance: Spot-check 0° Aries (sidereal) = Ashwini 1; 26°40′ Pisces (sidereal) = Revati 4.

Vimshottari Dasha (120 years)
- Sequence & years: Ketu 7, Venus 20, Sun 6, Moon 10, Mars 7, Rahu 18, Jupiter 16, Saturn 19, Mercury 17 (cycle repeats).
- Start: dasha_lord of natal Moon’s nakshatra; proportion remaining by Moon’s pada remainder.
- Levels: Maha (D1) → Antar (D2) → Pratyantar (D3) → Sukshma (D4) → Prana (D5) (optional deeper levels).
- Output: list of spans with start/end ISO, level, lord.
- Acceptance: Timeline total spans add to 120y; continuity across level boundaries.

Panchānga flags (optional)
- Tithi: floor((Moon−Sun) / 12°) + 1 (1–30). Yoga: floor((Moon+Sun) / 13°20′) + 1 (1–27). Karana: half‑tithis.
- Vāra (weekday): from timezone‑aware local time.
- Gate usage: allow boosters for transits aligning with active dasha lord or nakshatra lord.

Profiles & Toggles
- `vedic.enabled` (default false), `ayanamsha` (Lahiri default), `dasha.levels` (1–5), `panchanga.flags:true|false`.

Interoperability
- Export additional fields under `context.vedic`: nakshatra, pada, dasha_level/lord, panchanga.
<!-- >>> AUTO-GEN END: Vedic Layer v1.0 (instructions) -->
