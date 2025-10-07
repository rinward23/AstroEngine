# Proposed Remediation Tasks

## Typographical issue
- **File:** `astroengine/cli_legacy.py`
- **Problem:** Zodiacal releasing summaries append the bare flag `"loosing"` when a period marks a loosing of the bond. The label lacks the "of the bond" wording and reads like an English misspelling in the CLI output (e.g., `"loosing"` appears by itself).
- **Suggested fix:** Update the CLI formatter to emit a descriptive phrase such as "loosing of the bond" so the terminology is spelled correctly and conveys the full concept.

## Bug
- **File:** `pyproject.toml`
- **Problem:** The documentation instructs developers to install the `fallback-ephemeris` optional dependency group (`pip install -e .[fallback-ephemeris]`), but that extra is missing from the packaging metadata. Attempting the documented command raises a packaging error.
- **Suggested fix:** Define a `fallback-ephemeris` optional dependency set in `pyproject.toml` (e.g., pulling in `pymeeus` and any other fallback requirements) so the documented install command succeeds.

## Documentation discrepancy
- **Files:** `docs/module/providers_and_frames.md`, `profiles/base_profile.yaml`
- **Problem:** The providers contract doc states that `profiles/base_profile.yaml` documents `providers.swe.delta_t`, but the base profile currently omits that key entirely.
- **Suggested fix:** Either add the documented `providers.swe.delta_t` field to the profile (mirroring the docs) or update the documentation to reflect the actual profile schema.

## Test improvement
- **File:** `tests/test_utils_hits_to_df.py`
- **Problem:** The DataFrame helper test checks column order and numeric coercion but never asserts that the `exact_time` column is converted to timezone-aware datetimes. A regression could silently leave the column as strings without failing the test.
- **Suggested fix:** Extend the test to assert that `exact_time` is of dtype `datetime64[ns, UTC]` (or that each entry has `tzinfo` set to UTC) after conversion.
