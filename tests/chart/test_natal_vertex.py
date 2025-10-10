"""Unit coverage for vertex/anti-vertex natal chart points."""

from __future__ import annotations

from datetime import datetime

import pytest

from astroengine.chart.natal import ChartLocation, compute_natal_chart
from astroengine.ephemeris import BodyPosition, HousePositions


class _StubAdapter:
    def __init__(self, vertex: float, antivertex: float) -> None:
        self._vertex = vertex
        self._antivertex = antivertex

    def julian_day(self, moment: datetime) -> float:
        return 2_451_545.0

    def body_positions(self, jd_ut: float, body_map: dict[str, int]) -> dict[str, BodyPosition]:
        positions: dict[str, BodyPosition] = {}
        for index, name in enumerate(body_map.keys()):
            positions[name] = BodyPosition(
                body=name,
                julian_day=jd_ut,
                longitude=float(index),
                latitude=0.0,
                distance_au=1.0,
                speed_longitude=0.0,
                speed_latitude=0.0,
                speed_distance=0.0,
                declination=0.0,
                speed_declination=0.0,
            )
        return positions

    def houses(self, jd_ut: float, latitude: float, longitude: float) -> HousePositions:
        cusps = tuple(float(degree) for degree in range(0, 360, 30))
        return HousePositions(
            system="placidus",
            cusps=cusps,
            ascendant=120.0,
            midheaven=210.0,
            vertex=self._vertex,
            antivertex=self._antivertex,
        )


@pytest.mark.parametrize(
    "vertex, antivertex",
    [
        (123.456, 303.456),
        (0.0, 180.0),
    ],
)
def test_compute_natal_chart_includes_vertex_points(vertex: float, antivertex: float) -> None:
    adapter = _StubAdapter(vertex, antivertex)
    moment = datetime(2020, 1, 1)
    location = ChartLocation(latitude=51.5, longitude=-0.1)

    chart = compute_natal_chart(
        moment,
        location,
        adapter=adapter,
        body_expansions={"vertex": True},
    )

    assert "Vertex" in chart.positions
    assert "Anti-Vertex" in chart.positions
    assert chart.positions["Vertex"].longitude == pytest.approx(chart.houses.vertex)
    assert chart.positions["Anti-Vertex"].longitude == pytest.approx(
        chart.houses.antivertex
    )
