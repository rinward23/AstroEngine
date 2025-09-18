<!-- >>> AUTO-GEN BEGIN: Export Schemas v1.0 (instructions) -->
Define versioned export schemas for CSV/Parquet/JSONL.

Fields (minimum):
- t_exact (ISO UTC), aspect, transiting_body, natal_point, orb_deg, severity, family,
- lon_transit, lon_natal, decl_transit?, notes?,
- provider, profile, ruleset_tag, ephemeris_checksum, scan_window_start, scan_window_end, tzid?, ayanamsha?, house_system?

Partitioning (Parquet): by natal_id/year.
CSV conventions: UTF-8, header row, comma-separated, RFC4180 escaping.
<!-- >>> AUTO-GEN END: Export Schemas v1.0 (instructions) -->
