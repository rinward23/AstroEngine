<!-- >>> AUTO-GEN BEGIN: ICS Export v1.0 (instructions) -->
Purpose: export exact events as .ics calendar entries.

Rules:
- One VEVENT per exact; DTSTART = t_exact (UTC); SUMMARY = "<body> <aspect> <point>".
- Optional PRIORITY from severity bands; DESCRIPTION includes provider/profile/ruleset tag.
- Calendar name includes natal_id and window.
- Timezones optional (default UTC); allow user tz in CLI.
Acceptance:
- Valid ICS loads in major calendar apps; round-trip t_exact preserved.
<!-- >>> AUTO-GEN END: ICS Export v1.0 (instructions) -->
