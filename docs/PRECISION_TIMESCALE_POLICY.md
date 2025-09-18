<!-- >>> AUTO-GEN BEGIN: Precision & Timescale v1.0 (instructions) -->
Timescales
- Internal eval: TT (Terrestrial Time). External I/O: UTC (ISO‑8601 Z). Provider may use TDB internally but returns TT‑consistent results.
- ΔT source: Espenak‑Meeus fit for historical dates; JPL DE metadata for modern epoch; document version.

Error Budgets (target max absolute longitudinal error at exacts)
- Sun/Moon: ≤ 0.1″; inner planets: ≤ 0.5″; outer planets: ≤ 1.0″; Nodes: ≤ 6″.

Refinement
- Secant → bisection fallback; stop when |f| < 1e−6 deg or time step < 0.5 s.
- Retro/station guards: avoid oscillation by bracketing across sign changes of speed.

Acceptance
- Cross‑backend parity within budgets on sampled windows; reproducible timestamps within ±1 s for exacts (non‑lunar), ±5 s (lunar).
<!-- >>> AUTO-GEN END: Precision & Timescale v1.0 (instructions) -->
