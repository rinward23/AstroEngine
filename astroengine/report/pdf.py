"""Utility helpers for rendering compact chart PDFs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Sequence
from html import escape

from weasyprint import HTML

__all__ = [
    "WheelEntry",
    "AspectEntry",
    "ChartReportContext",
    "render_chart_pdf",
]


@dataclass(slots=True)
class WheelEntry:
    """Represents a single body position in the rendered wheel."""

    body: str
    sign: str
    degree: float
    longitude: float
    house: int | None = None


@dataclass(slots=True)
class AspectEntry:
    """Represents an aspect entry between two chart bodies."""

    body_a: str
    body_b: str
    aspect: str
    orb: float
    separation: float


@dataclass(slots=True)
class ChartReportContext:
    """Input payload used to render the PDF report."""

    title: str
    subtitle: str
    generated_at: datetime
    wheel: Sequence[WheelEntry]
    aspects: Sequence[AspectEntry]
    narrative: str
    disclaimers: Sequence[str]


def _format_degree(value: float) -> str:
    return f"{value:05.2f}°"


def _build_wheel_table(entries: Iterable[WheelEntry]) -> str:
    rows: list[str] = []
    for entry in entries:
        house_text = str(entry.house) if entry.house is not None else "—"
        rows.append(
            "<tr>"
            f"<td>{escape(entry.body)}</td>"
            f"<td>{escape(entry.sign)}</td>"
            f"<td>{_format_degree(entry.degree)}</td>"
            f"<td>{_format_degree(entry.longitude)}</td>"
            f"<td>{house_text}</td>"
            "</tr>"
        )
    return "".join(rows)


def _build_aspects_table(entries: Iterable[AspectEntry]) -> str:
    rows: list[str] = []
    for entry in entries:
        rows.append(
            "<tr>"
            f"<td>{escape(entry.body_a)}</td>"
            f"<td>{escape(entry.body_b)}</td>"
            f"<td>{escape(entry.aspect)}</td>"
            f"<td>{entry.separation:05.2f}°</td>"
            f"<td>{entry.orb:05.2f}°</td>"
            "</tr>"
        )
    return "".join(rows)


def render_chart_pdf(context: ChartReportContext) -> bytes:
    """Render the provided context to PDF bytes using WeasyPrint."""

    wheel_rows = _build_wheel_table(context.wheel)
    aspect_rows = _build_aspects_table(context.aspects)
    disclaimers = "".join(
        f"<li>{escape(line)}</li>" for line in context.disclaimers if line.strip()
    ) or "<li>Report provided for educational purposes only.</li>"
    html = f"""
    <html>
      <head>
        <meta charset="utf-8" />
        <style>
          body {{ font-family: 'Inter', 'Helvetica Neue', Helvetica, Arial, sans-serif; margin: 24px; color: #111827; }}
          h1 {{ font-size: 28px; margin-bottom: 0; }}
          h2 {{ margin-top: 24px; font-size: 20px; border-bottom: 1px solid #e5e7eb; padding-bottom: 4px; }}
          h3 {{ margin-top: 18px; font-size: 16px; }}
          p.meta {{ color: #6b7280; font-size: 12px; margin-top: 4px; }}
          table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 12px; }}
          th, td {{ border: 1px solid #e5e7eb; padding: 6px; text-align: left; }}
          th {{ background-color: #f3f4f6; text-transform: uppercase; font-size: 11px; letter-spacing: 0.05em; }}
          ul {{ font-size: 11px; color: #374151; }}
          .narrative {{ font-size: 13px; line-height: 1.5; margin-top: 12px; }}
        </style>
      </head>
      <body>
        <h1>{escape(context.title)}</h1>
        <p class="meta">{escape(context.subtitle)} · Generated {escape(context.generated_at.isoformat())}</p>
        <h2>Chart Wheel Overview</h2>
        <table>
          <thead>
            <tr><th>Body</th><th>Sign</th><th>Sign Degree</th><th>Ecliptic Longitude</th><th>House</th></tr>
          </thead>
          <tbody>{wheel_rows}</tbody>
        </table>
        <h2>Aspect Summary</h2>
        <table>
          <thead>
            <tr><th>Body A</th><th>Body B</th><th>Aspect</th><th>Separation</th><th>Orb</th></tr>
          </thead>
          <tbody>{aspect_rows}</tbody>
        </table>
        <h2>Narrative Summary</h2>
        <p class="narrative">{escape(context.narrative)}</p>
        <h3>Disclaimers</h3>
        <ul>{disclaimers}</ul>
      </body>
    </html>
    """
    document = HTML(string=html)
    return document.write_pdf()
