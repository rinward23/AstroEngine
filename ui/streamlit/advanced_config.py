from __future__ import annotations

import math

import streamlit as st

from astroengine.config import config_path, save_settings
from astroengine.runtime_config import runtime_settings

st.set_page_config(
    page_title="AstroEngine – Advanced Config (All Options)", layout="wide"
)
st.title("⚙️ Advanced Configuration — Everything, with Explanations")


def slider_number(
    label: str,
    key: str,
    value: float,
    minv: float,
    maxv: float,
    step: float,
    help: str | None = None,
):
    """Render a slider + numeric input pair kept in sync via session state."""

    if key not in st.session_state:
        st.session_state[key] = float(value)

    slider_col, number_col = st.columns([3, 1])
    with slider_col:
        st.session_state[key] = st.slider(
            label,
            min_value=float(minv),
            max_value=float(maxv),
            value=float(st.session_state[key]),
            step=float(step),
            help=help,
            key=f"{key}_slider",
        )
    with number_col:
        st.session_state[key] = st.number_input(
            " ",
            value=float(st.session_state[key]),
            min_value=float(minv),
            max_value=float(maxv),
            step=float(step),
            key=f"{key}_num",
        )
    return st.session_state[key]


cur = runtime_settings.persisted()

# ---------- Aspects ----------------------------------------------------------
st.header("Aspects & Orbs")
aspect_cols = st.columns(2)
with aspect_cols[0]:
    st.subheader("Orbs")
    st.caption(
        "Higher orbs include more hits but add noise; lower orbs emphasize precision."
    )
    cur.aspects.orbs_global = slider_number(
        "Global Orb (°)",
        "as_orb_global",
        cur.aspects.orbs_global,
        0.0,
        12.0,
        0.25,
        "Modern practice typically keeps most aspect orbs ≤ 8°. Sun/Moon can be wider.",
    )

    default_rows = [
        ("conjunction", 0.0, 12.0),
        ("opposition", 0.0, 12.0),
        ("trine", 0.0, 12.0),
        ("square", 0.0, 12.0),
        ("sextile", 0.0, 12.0),
        ("quincunx", 0.0, 12.0),
        ("semisextile", 0.0, 12.0),
        ("sesquisquare", 0.0, 12.0),
        ("quintile", 0.0, 12.0),
        ("biquintile", 0.0, 12.0),
    ]
    aspect_cols_nested = st.columns(2)
    orb_by_aspect = cur.aspects.orbs_by_aspect.copy()
    for idx, (name, low, high) in enumerate(default_rows):
        with aspect_cols_nested[idx % 2]:
            val = orb_by_aspect.get(name, cur.aspects.orbs_global)
            orb_by_aspect[name] = slider_number(
                name.title(),
                f"orb_aspect_{name}",
                float(val),
                low,
                high,
                0.25,
                "Adjust tolerance for this specific aspect.",
            )
    cur.aspects.orbs_by_aspect = orb_by_aspect

with aspect_cols[1]:
    st.subheader("Bias & Scaling")
    cur.aspects.applying_bonus_deg = slider_number(
        "Applying Bonus (°)",
        "app_bonus",
        cur.aspects.applying_bonus_deg,
        0.0,
        3.0,
        0.1,
        "How much tighter to treat applying aspects (lower = stricter)",
    )
    cur.aspects.separating_penalty_deg = slider_number(
        "Separating Penalty (°)",
        "sep_penalty",
        cur.aspects.separating_penalty_deg,
        0.0,
        3.0,
        0.1,
        "How much looser to consider separating aspects (higher = fewer shown)",
    )
    cur.aspects.orb_scaling = st.selectbox(
        "Orb Scaling Mode",
        ["none", "luminary_priority", "magnitude"],
        index=["none", "luminary_priority", "magnitude"].index(
            cur.aspects.orb_scaling
        ),
        help=(
            "Luminary priority widens orbs for Sun/Moon; magnitude scales orbs by "
            "visual prominence (if star data is used)."
        ),
    )
    cur.aspects.harmonics_n = int(
        slider_number(
            "Harmonics (n)",
            "harmonics_n",
            cur.aspects.harmonics_n,
            1,
            32,
            1,
            "Higher n finds more fine-grained harmonic aspects; keep modest for clarity.",
        )
    )

st.subheader("Per-Body Orbs")
body_cols = st.columns(2)
orbs_by_body = cur.aspects.orbs_by_body.copy()
body_defaults: list[tuple[str, float, float, float, str]] = [
    ("sun", 0.0, 15.0, 0.5, "Sun aspects often use the widest orbs."),
    ("moon", 0.0, 15.0, 0.5, "Moon next widest; personal planets mid-range; outers narrow."),
    ("mercury", 0.0, 12.0, 0.5, ""),
    ("venus", 0.0, 12.0, 0.5, ""),
    ("mars", 0.0, 10.0, 0.5, ""),
    ("jupiter", 0.0, 8.0, 0.5, ""),
    ("saturn", 0.0, 8.0, 0.5, ""),
    ("uranus", 0.0, 6.0, 0.5, ""),
    ("neptune", 0.0, 6.0, 0.5, ""),
    ("pluto", 0.0, 6.0, 0.5, ""),
]
for idx, (name, low, high, step, hint) in enumerate(body_defaults):
    with body_cols[idx % 2]:
        current = orbs_by_body.get(name, high / 2)
        orbs_by_body[name] = slider_number(
            name.title(),
            f"orb_body_{name}",
            float(current),
            low,
            high,
            step,
            hint,
        )
cur.aspects.orbs_by_body = orbs_by_body

st.subheader("Aspect Weights (influence on sorting/scoring)")
weight_cols = st.columns(2)
weights = cur.aspects.weights_by_aspect.copy()
for idx, name in enumerate(
    [
        "conjunction",
        "opposition",
        "trine",
        "square",
        "sextile",
        "quincunx",
        "semisextile",
        "sesquisquare",
        "quintile",
        "biquintile",
    ]
):
    with weight_cols[idx % 2]:
        weights[name] = int(
            slider_number(
                f"{name.title()} (−10..+10)",
                f"w_{name}",
                float(weights.get(name, 1)),
                -10,
                10,
                1,
                "Higher weight = more prominent in lists; negative deemphasizes.",
            )
        )
cur.aspects.weights_by_aspect = weights

# ---------- Patterns ---------------------------------------------------------
st.header("Pattern Detection")
st.caption(
    "Detect motifs like T‑squares, Grand Trines, Yods. Tighter tolerances show fewer but cleaner patterns."
)
cur.aspects.detect_patterns = st.toggle(
    "Enable pattern detection", value=cur.aspects.detect_patterns
)
cur.aspects.pattern_tolerance_deg = slider_number(
    "Pattern tolerance (°)",
    "pattern_tol",
    cur.aspects.pattern_tolerance_deg,
    0.5,
    5.0,
    0.25,
    "Maximum deviation from ideal angles within a pattern.",
)
st.info(
    "Pattern tolerance is applied inside the detector; this value will be read by the engine where applicable."
)

# ---------- Dignities --------------------------------------------------------
st.header("Dignities & Planetary Condition")
st.caption(
    "Set how dignity/condition contributes to reports. Weights reflect classical practice; tune to taste."
)
dignity_weights = cur.dignities.weights
weight_rows = [
    ("Domicile", "domicile"),
    ("Exaltation", "exaltation"),
    ("Triplicity", "triplicity"),
    ("Term", "term"),
    ("Face", "face"),
    ("Detriment", "detriment"),
    ("Fall", "fall"),
    ("Peregrine", "peregrine"),
    ("Angular", "angular"),
    ("Succedent", "succedent"),
    ("Cadent", "cadent"),
    ("Retrograde", "retrograde"),
    ("Combustion", "combustion"),
    ("Cazimi", "cazimi"),
    ("Under Beams", "under_beams"),
]
dignity_cols = st.columns(2)
for idx, (label, attr) in enumerate(weight_rows):
    with dignity_cols[idx % 2]:
        new_value = slider_number(
            f"{label} (−10..+10)",
            f"dig_{attr}",
            float(getattr(dignity_weights, attr)),
            -10,
            10,
            1,
            "Positive increases favor; negative penalizes condition.",
        )
        setattr(dignity_weights, attr, int(round(new_value)))
cur.dignities.show_breakdown = st.toggle(
    "Show breakdown in reports", value=cur.dignities.show_breakdown
)
cur.dignities.normalize_to_scale = int(
    slider_number(
        "Normalize totals to (0..N)",
        "dig_norm",
        float(cur.dignities.normalize_to_scale),
        0,
        200,
        10,
        "0 disables normalization; otherwise scales totals to the chosen ceiling.",
    )
)

# ---------- Houses -----------------------------------------------------------
st.header("Houses")
cur.houses.topocentric = st.toggle(
    "Use topocentric calculations where applicable", value=cur.houses.topocentric
)
cur.houses.house_offset_deg = slider_number(
    "House cusp visual offset (°)",
    "house_off",
    cur.houses.house_offset_deg,
    0.0,
    2.0,
    0.1,
    "Purely visual smoothing for rendering; does not change calculations.",
)
cur.houses.zero_based_numbering = st.toggle(
    "Zero-based house numbering (experimental)",
    value=cur.houses.zero_based_numbering,
)

# ---------- Rendering --------------------------------------------------------
st.header("Rendering")
cur.rendering.theme = st.selectbox(
    "Theme",
    ["dark", "light", "high_contrast"],
    index=["dark", "light", "high_contrast"].index(cur.rendering.theme),
)
cur.rendering.glyph_set = st.selectbox(
    "Glyph set",
    ["default", "classic", "modern"],
    index=["default", "classic", "modern"].index(cur.rendering.glyph_set),
)
cur.rendering.line_thickness = slider_number(
    "Aspect line thickness (px)",
    "line_thick",
    cur.rendering.line_thickness,
    0.5,
    5.0,
    0.1,
    "Thicker lines emphasize aspects; thinner declutters.",
)
cur.rendering.grid_density = int(
    slider_number(
        "Grid density",
        "grid_den",
        cur.rendering.grid_density,
        3,
        12,
        1,
        "Higher density shows more ticks/labels around the wheel.",
    )
)
cur.rendering.star_mag_limit = slider_number(
    "Fixed star magnitude cut-off",
    "mag_cut",
    cur.rendering.star_mag_limit,
    -1.5,
    8.0,
    0.1,
    "Lower (brighter) includes only prominent stars; higher includes fainter.",
)

# ---------- Forecasting ------------------------------------------------------
st.header("Forecast Stacks")
cur.forecast_stack.exactness_deg = slider_number(
    "Exactness threshold (°)",
    "fc_exact",
    cur.forecast_stack.exactness_deg,
    0.0,
    3.0,
    0.05,
    "Hits within this orb count as exact for stacking/merging.",
)
cur.forecast_stack.consolidate_hours = int(
    slider_number(
        "Consolidate events within (hours)",
        "fc_cons",
        cur.forecast_stack.consolidate_hours,
        1,
        168,
        1,
        "Merges near-identical hits to reduce noise.",
    )
)
cur.forecast_stack.min_orb_deg = slider_number(
    "Minimum orb to include (°)",
    "fc_min_orb",
    cur.forecast_stack.min_orb_deg,
    0.0,
    3.0,
    0.05,
    "Filters ultra-wide/weak hits.",
)

# ---------- Electional -------------------------------------------------------
st.header("Electional Weights & Step")
electional_weights = cur.electional.weights
electional_rows = [
    ("Benefic on angles", "benefic_on_angles", "Rewards Venus/Jupiter culminating/rising."),
    ("Malefic on angles", "malefic_on_angles", "Penalizes Mars/Saturn on angles."),
    ("Moon void of course", "moon_void", "Penalizes void Moon windows."),
    ("Dignity bonus", "dignity_bonus", "Rewards dignified sign placements."),
    ("Retrograde penalty", "retrograde_penalty", "Penalizes retrograde planets."),
    ("Combustion penalty", "combustion_penalty", "Sun within ~8° of planet."),
    ("Cazimi bonus", "cazimi_bonus", "Sun within ~0.5° of planet."),
]
electional_cols = st.columns(2)
for idx, (label, attr, help_text) in enumerate(electional_rows):
    with electional_cols[idx % 2]:
        new_val = slider_number(
            f"{label} (−10..+10)",
            f"el_{attr}",
            float(getattr(electional_weights, attr)),
            -10,
            10,
            1,
            help_text,
        )
        setattr(electional_weights, attr, int(round(new_val)))
cur.electional.step_minutes = int(
    slider_number(
        "Search step (minutes)",
        "el_step",
        cur.electional.step_minutes,
        1,
        60,
        1,
        "Smaller finds more candidates but is slower.",
    )
)

# ---------- Declinations -----------------------------------------------------
st.header("Declinations")
cur.declinations.orb_deg = slider_number(
    "Parallel/contra orb (°)",
    "dec_orb",
    cur.declinations.orb_deg,
    0.0,
    2.0,
    0.05,
    "Keep small for meaningful parallels (0.5°–1.0° typical).",
)

# ---------- Swiss caps -------------------------------------------------------
st.header("Swiss Ephemeris Caps")
swiss_col_min, swiss_col_max, swiss_col_btn = st.columns([1, 1, 2])
with swiss_col_min:
    min_year = int(
        st.number_input(
            "Min year",
            value=int(cur.swiss_caps.min_year),
            min_value=1,
            max_value=9999,
            step=10,
            help="Lower bound of supported calculations.",
        )
    )
with swiss_col_max:
    max_year = int(
        st.number_input(
            "Max year",
            value=int(cur.swiss_caps.max_year),
            min_value=1,
            max_value=9999,
            step=10,
            help="Upper bound; probe ensures your data can handle it.",
        )
    )
with swiss_col_btn:
    if st.button("Probe capability"):
        try:
            from astroengine.ephemeris.swe import swe
            def _can(year: int) -> bool:
                jd = swe().julday(year, 1, 1, 12.0)
                position = swe().calc_ut(jd, swe().SUN)
                return isinstance(position, tuple) and not any(
                    math.isnan(val) for val in position[0]
                )

            if _can(min_year) and _can(max_year):
                st.success("Swiss computations succeeded at both boundaries.")
            else:
                st.warning(
                    "Swiss failed at a boundary; narrow the range or install full ephemeris data."
                )
        except Exception as exc:  # pragma: no cover - UI feedback only
            st.info(f"Swiss probe unavailable: {exc}")

# ---------- Observability & Performance -------------------------------------
st.header("Observability & Performance")
cur.observability.otel_enabled = st.toggle(
    "Enable OpenTelemetry traces", value=cur.observability.otel_enabled
)
cur.observability.sampling_ratio = slider_number(
    "Trace sampling ratio",
    "otel_samp",
    cur.observability.sampling_ratio,
    0.0,
    1.0,
    0.01,
    "Fraction of requests to sample for tracing.",
)
cur.perf.workers = int(
    slider_number(
        "Workers",
        "perf_workers",
        cur.perf.workers,
        1,
        8,
        1,
        "More workers increase concurrency (CPU permitting).",
    )
)
cur.perf.batch_size = int(
    slider_number(
        "Batch size",
        "perf_batch",
        cur.perf.batch_size,
        64,
        8192,
        64,
        "Larger batches reduce overhead but increase memory usage.",
    )
)

# ---------- Chat Copilot -----------------------------------------------------
st.header("Chat Copilot")
cur.chat.enabled = st.toggle("Enable Chat panel", value=cur.chat.enabled)
cur.chat.model = st.text_input(
    "Model",
    value=cur.chat.model,
    help="e.g., gpt-4o-mini, gpt-4.1-mini",
)
cur.chat.temperature = slider_number(
    "Creativity (temperature)",
    "chat_temp",
    cur.chat.temperature,
    0.0,
    2.0,
    0.05,
    "Lower is deterministic; higher is more creative.",
)
cur.chat.max_tokens = int(
    slider_number(
        "Max tokens per reply",
        "chat_maxtok",
        cur.chat.max_tokens,
        100,
        32000,
        100,
        "Upper bound for a single response.",
    )
)
cur.chat.token_budget_session = int(
    slider_number(
        "Session token budget",
        "chat_budget",
        cur.chat.token_budget_session,
        1000,
        1_000_000,
        1000,
        "Soft cap to prevent runaway usage.",
    )
)
cur.chat.tools_enabled = st.toggle(
    "Allow tool/command usage", value=cur.chat.tools_enabled
)

# ---------- Save / Reset -----------------------------------------------------
button_col_save, button_col_reset = st.columns(2)
with button_col_save:
    if st.button("💾 Save All", type="primary"):
        cur.swiss_caps.min_year = min_year
        cur.swiss_caps.max_year = max_year
        save_settings(cur)
        runtime_settings.cache_persisted(cur)
        st.success(f"Saved to {config_path()}")
with button_col_reset:
    if st.button("Reset to Defaults"):
        from astroengine.config import default_settings

        defaults = default_settings()
        defaults.ephemeris.path = cur.ephemeris.path
        save_settings(defaults)
        runtime_settings.cache_persisted(defaults)
        st.success("Defaults restored.")
