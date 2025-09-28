"""Grid builders for synastry inter-aspects."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from .models import GridCell, Hit

__all__ = ["build_grid"]


_MAJOR_ASPECTS = frozenset({0, 60, 90, 120, 180})
_FLOAT_EPS = 1e-9


def _is_major(aspect: int) -> bool:
    return aspect in _MAJOR_ASPECTS


def _better_candidate(candidate: Hit, current: Hit | None) -> bool:
    if current is None:
        return True
    if abs(candidate.severity - current.severity) > _FLOAT_EPS:
        return candidate.severity > current.severity
    major_candidate = _is_major(candidate.aspect)
    major_current = _is_major(current.aspect)
    if major_candidate != major_current:
        return major_candidate
    if abs(candidate.delta - current.delta) > _FLOAT_EPS:
        return candidate.delta < current.delta
    return (
        candidate.aspect,
        candidate.body_a.lower(),
        candidate.body_b.lower(),
    ) < (
        current.aspect,
        current.body_a.lower(),
        current.body_b.lower(),
    )


def build_grid(
    hits: Iterable[Hit],
    bodies_a: Sequence[str],
    bodies_b: Sequence[str],
) -> dict[str, dict[str, GridCell]]:
    """Return matrix selecting the strongest hit for each body pair."""

    best: dict[tuple[str, str], Hit] = {}
    for hit in hits:
        key = (hit.body_a, hit.body_b)
        current = best.get(key)
        if _better_candidate(hit, current):
            best[key] = hit

    grid: dict[str, dict[str, GridCell]] = {}
    for body_a in bodies_a:
        row: dict[str, GridCell] = {}
        for body_b in bodies_b:
            row[body_b] = GridCell(best=best.get((body_a, body_b)))
        grid[body_a] = row
    return grid

