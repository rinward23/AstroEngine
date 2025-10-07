"""Vectorised detection of synastry inter-aspects."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from astroengine.core.bodies import canonical_name

from .models import ChartPositions, Hit
from .policy import OrbPolicy

__all__ = ["detect_hits"]


_NODE_CANONICALS = {
    "true_node",
    "mean_node",
    "north_node",
    "south_node",
    "node",
}


def _is_node(body: str) -> bool:
    return canonical_name(body) in _NODE_CANONICALS


def _prepare(chart: ChartPositions) -> tuple[list[str], list[str], np.ndarray]:
    names: list[str] = []
    canonical_names: list[str] = []
    longitudes: list[float] = []
    for name, lon in chart.iter_longitudes():
        names.append(name)
        canonical_names.append(chart.canonical_name_for(name))
        longitudes.append(lon)
    if not longitudes:
        return [], [], np.empty((0,), dtype=float)
    return names, canonical_names, np.asarray(longitudes, dtype=float)


def _pairwise_separation(lons_a: np.ndarray, lons_b: np.ndarray, nodes_a: np.ndarray, nodes_b: np.ndarray) -> np.ndarray:
    if lons_a.size == 0 or lons_b.size == 0:
        return np.empty((lons_a.size, lons_b.size))

    diff = (lons_a[:, None] - lons_b[None, :])
    separation = np.abs(((diff + 180.0) % 360.0) - 180.0)

    if nodes_a.any():
        node_lons = lons_a[nodes_a][:, None]
        other = lons_b[None, :]
        node_delta = np.minimum(
            np.abs(((node_lons - other + 180.0) % 360.0) - 180.0),
            np.abs((((node_lons + 180.0) - other + 180.0) % 360.0) - 180.0),
        )
        separation[nodes_a, :] = node_delta

    if nodes_b.any():
        node_lons = lons_b[nodes_b]
        other = lons_a[:, None]
        node_delta = np.minimum(
            np.abs(((other - node_lons + 180.0) % 360.0) - 180.0),
            np.abs(((other - (node_lons + 180.0) + 180.0) % 360.0) - 180.0),
        )
        separation[:, nodes_b] = node_delta

    return separation


def detect_hits(
    pos_a: ChartPositions,
    pos_b: ChartPositions,
    *,
    aspects: Sequence[int],
    policy: OrbPolicy,
    gamma: float = 1.0,
) -> list[Hit]:
    """Return a list of :class:`Hit` within the configured orb policy."""

    names_a, canonical_a, lons_a = _prepare(pos_a)
    names_b, canonical_b, lons_b = _prepare(pos_b)

    if not len(lons_a) or not len(lons_b):
        return []

    nodes_a = np.array([_is_node(name) for name in canonical_a], dtype=bool)
    nodes_b = np.array([_is_node(name) for name in canonical_b], dtype=bool)

    separation = _pairwise_separation(lons_a, lons_b, nodes_a, nodes_b)

    base_orbs = np.empty_like(separation, dtype=float)
    for i, body_a in enumerate(names_a):
        for j, body_b in enumerate(names_b):
            base_orbs[i, j] = policy.base_orb(body_a, body_b)

    hits: list[Hit] = []
    aspects_list = [int(a) for a in aspects]
    aspects_list.sort()

    for aspect in aspects_list:
        cap = policy.cap(aspect)
        effective = np.minimum(base_orbs, cap)
        epsilon = np.abs(separation - float(aspect))
        mask = epsilon <= (effective + 1e-9)
        if not mask.any():
            continue

        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = np.zeros_like(epsilon)
            positive_orb = effective > 1e-9
            ratio[positive_orb] = np.clip(
                epsilon[positive_orb] / effective[positive_orb], 0.0, 1.0
            )
            severity = 0.5 * (1.0 + np.cos(np.pi * ratio))
            if gamma != 1.0:
                severity = severity**float(gamma)
            zero_orb = ~positive_orb
            severity[zero_orb] = np.where(
                epsilon[zero_orb] <= 1e-9, 1.0, 0.0
            )

        severity = np.where(mask, severity, 0.0)

        idx_i, idx_j = np.nonzero(mask)
        for i, j in zip(idx_i.tolist(), idx_j.tolist(), strict=False):
            orb_eff = float(effective[i, j])
            eps = float(epsilon[i, j])
            sev = float(max(0.0, min(1.0, severity[i, j])))
            if orb_eff <= 0.0 and eps > 1e-9:
                continue
            hits.append(
                Hit(
                    bodyA=names_a[i],
                    bodyB=names_b[j],
                    aspect=int(aspect),
                    delta=eps,
                    orb=orb_eff,
                    severity=sev,
                    separation=float(separation[i, j]),
                )
            )

    hits.sort(
        key=lambda h: (
            -h.severity,
            h.delta,
            h.aspect,
            h.body_a.lower(),
            h.body_b.lower(),
        )
    )
    return hits

