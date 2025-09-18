<!-- >>> AUTO-GEN BEGIN: Atlas & TZ v1.0 (instructions) -->
Inputs:
- lat, lon, place_name?, datetime_local, tzid? (if tzid missing, resolve via timezonefinder).

Rules:
- Resolve tzid via coordinates; compute historical UTC offset via tzdb.
- Document DST transitions and ambiguous times; require explicit disambiguation.
- Do not embed proprietary atlases; document OSM/Nominatim usage & rate limits.
<!-- >>> AUTO-GEN END: Atlas & TZ v1.0 (instructions) -->
