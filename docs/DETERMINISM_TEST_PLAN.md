<!-- >>> AUTO-GEN BEGIN: Determinism Tests v1.0 (instructions) -->
Goal: identical inputs produce byte-for-byte identical outputs.

Plan:
- Golden JSONL for 3 scenarios (30-day windows) stored under tests/golden/.
- Event list canonicalization: sort by t_exact, body, aspect, point; fixed float rounding.
- Hash: SHA256 of canonical JSONL; compare against golden.
- CI: fail if hash drifts; allow explicit update via env flag.
- Ephemeris checksum recorded in outputs; CI uses pinned cache.
<!-- >>> AUTO-GEN END: Determinism Tests v1.0 (instructions) -->
