"""Solar arc aspect detectors (currently gated behind experimental flag)."""

from __future__ import annotations

from collections.abc import Sequence


def solar_arc_natal_aspects(
    natal_ts: str,
    start_ts: str,
    end_ts: str,
    *,
    aspects: Sequence[int],
    orb_deg: float,
) -> list[object]:
    raise NotImplementedError(
        "'solar_arc_natal_aspects' is experimental and disabled by default. "
        "Enable the experimental modality flag before wiring this detector."
    )


__all__ = ["solar_arc_natal_aspects"]
