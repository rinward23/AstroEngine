"""Streamlit helpers for rendering the system doctor report."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

import streamlit as st

STATUS_ICONS: Mapping[str, str] = {"ok": "✅", "warn": "⚠️", "error": "❌"}

REMEDIATION_TIPS: Mapping[str, Mapping[str, Iterable[str]]] = {
    "swiss_ephemeris": {
        "warn": (
            "Ensure the `SE_EPHE_PATH` environment variable points to a directory containing Swiss Ephemeris data.",
            "Verify the configured Swiss range covers the requested years in settings.",
        ),
        "error": (
            "Install the `pyswisseph` Python package in the environment running the API.",
            "Download the Swiss Ephemeris `.se1` files and update `SE_EPHE_PATH` to their location.",
        ),
    },
    "database": {
        "warn": (
            "Confirm the database server is reachable using the configured SQLAlchemy URL.",
        ),
        "error": (
            "Check database credentials and run `alembic upgrade head` to recreate missing schema objects.",
        ),
    },
    "migrations": {
        "warn": (
            "Run `alembic upgrade head` to align the database with the latest schema revisions.",
        ),
        "error": (
            "Apply outstanding Alembic migrations before serving API requests.",
        ),
    },
    "cache": {
        "warn": (
            "Clear the AstroEngine cache directory (`~/.astroengine/cache`) if the integrity check is inconclusive.",
        ),
        "error": (
            "Verify the process can read and write `positions.sqlite`, then rerun the API to rebuild the cache.",
        ),
    },
    "settings": {
        "warn": (
            "Open the Settings editor and confirm Swiss caps, performance, and observability values are sensible.",
        ),
        "error": (
            "Update the Settings file so `swiss_caps.min_year` is less than `max_year` and caching values are positive.",
        ),
    },
    "disk": {
        "warn": (
            "Free up space near the AstroEngine home directory or move caches to a larger volume.",
        ),
        "error": (
            "Stop the service and reclaim disk capacity; the process cannot operate reliably with critically low space.",
        ),
    },
}

DEFAULT_REMEDIATION: Mapping[str, Iterable[str]] = {
    "warn": ("Review recent logs for warnings and confirm configuration defaults are acceptable.",),
    "error": ("Inspect server logs for stack traces and correct the failing subsystem before retrying.",),
}


def _remediation(check_name: str, status: str) -> Iterable[str]:
    scoped = REMEDIATION_TIPS.get(check_name.lower())
    if scoped:
        tips = scoped.get(status)
        if tips:
            return tips
    fallback = DEFAULT_REMEDIATION.get(status)
    return fallback or ()


def render_report(report: Mapping[str, Any]) -> None:
    """Render the doctor report with remediation guidance."""

    overall_status = str(report.get("status", "warn"))
    generated_at = report.get("generated_at")

    cols = st.columns(2)
    with cols[0]:
        st.metric(
            "Overall Status",
            overall_status.upper(),
            help="Worst severity across Swiss Ephemeris, database, migration, cache, settings, and disk checks.",
        )
    with cols[1]:
        st.metric("Generated", generated_at or "n/a")

    checks = report.get("checks", {})
    if not isinstance(checks, Mapping):  # pragma: no cover - defensive UI guard
        st.warning("Doctor report did not include detailed checks.")
        return

    for name in sorted(checks):
        payload = checks.get(name)
        if not isinstance(payload, Mapping):  # pragma: no cover - defensive UI guard
            continue
        status = str(payload.get("status", "warn"))
        icon = STATUS_ICONS.get(status, "❔")
        detail = payload.get("detail", "")
        header = f"{icon} {name.replace('_', ' ').title()}"
        expanded = status != "ok"
        with st.expander(header, expanded=expanded):
            if detail:
                st.write(detail)
            data = payload.get("data")
            if isinstance(data, Mapping) and data:
                st.json(data)
            elif data:
                st.write(data)

            tips = tuple(_remediation(name, status))
            if tips:
                st.markdown("**Remediation**")
                for tip in tips:
                    st.markdown(f"- {tip}")

    st.caption(
        "Results derive from live Swiss Ephemeris, database, migration, cache, settings, and disk diagnostics."
    )


__all__ = ["render_report"]
