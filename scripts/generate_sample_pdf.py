"""Generate a deterministic sample PDF report using real chart data."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from astroengine.chart.natal import ChartLocation, compute_natal_chart
from astroengine.config import default_settings
from astroengine.report import build_chart_report_context, render_chart_pdf


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("generated/reports/sample_chart_report.pdf"),
        help="Path where the sample PDF will be written.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Use well-known chart details so the output is reproducible and backed by
    # actual ephemeris calculations.
    moment = datetime(1987, 6, 15, 6, 30, tzinfo=timezone.utc)
    location = ChartLocation(latitude=37.7749, longitude=-122.4194)
    try:
        natal = compute_natal_chart(moment, location)
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on local deps
        if "swisseph" in str(exc).lower():
            raise SystemExit(
                "swisseph is required to generate the sample PDF. Install it with "
                "`pip install pyswisseph` or include the `pyswisseph` extra when "
                "installing AstroEngine."
            ) from exc
        raise

    settings = default_settings()
    context = build_chart_report_context(
        chart_id=1,
        natal=natal,
        chart_kind="natal",
        profile_key="sample",
        chart_timestamp=moment,
        location_name="San Francisco, CA",
        disclaimers=settings.reports.disclaimers,
        generated_at=datetime.now(timezone.utc),
    )
    args.output.write_bytes(render_chart_pdf(context))
    print(f"Sample PDF written to {args.output}")


if __name__ == "__main__":
    main()

