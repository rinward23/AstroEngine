"""Progressed chart aspect detectors gated behind experimental flags."""

from __future__ import annotations

from collections.abc import Sequence


def progressed_natal_aspects(
    natal_ts: str,
    start_ts: str,
    end_ts: str,
    *,
    aspects: Sequence[int],
    orb_deg: float,
) -> list[object]:
    raise NotImplementedError(
        "'progressed_natal_aspects' is experimental and disabled by default. "
        "Enable the experimental modality flag before wiring this detector."
    )


__all__ = ["progressed_natal_aspects"]
