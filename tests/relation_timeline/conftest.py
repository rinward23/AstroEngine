from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Mapping

import pytest

from astroengine.ephemeris.adapter import EphemerisSample


@dataclass
class LinearEphemeris:
    epoch: dt.datetime
    base_longitudes: Mapping[int, float]
    rates_deg_per_day: Mapping[int, float]

    def sample(self, body: int, moment: dt.datetime) -> EphemerisSample:
        delta_days = (moment - self.epoch).total_seconds() / 86400.0
        base = self.base_longitudes.get(body, 0.0)
        rate = self.rates_deg_per_day.get(body, 0.0)
        longitude = (base + rate * delta_days) % 360.0
        return EphemerisSample(
            jd_tt=0.0,
            jd_utc=0.0,
            longitude=longitude,
            latitude=0.0,
            distance=1.0,
            speed_longitude=rate,
            speed_latitude=0.0,
            speed_distance=0.0,
            right_ascension=0.0,
            declination=0.0,
            speed_right_ascension=0.0,
            speed_declination=0.0,
            delta_t_seconds=0.0,
        )


@pytest.fixture
def timeline_epoch() -> dt.datetime:
    return dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc)


@pytest.fixture
def body_ids() -> dict[str, int]:
    return {"Venus": 1, "Mars": 2, "Jupiter": 3, "Saturn": 4}


@pytest.fixture
def linear_ephemeris(timeline_epoch: dt.datetime) -> LinearEphemeris:
    base = {1: 0.0, 2: 10.0, 3: 20.0, 4: 40.0}
    rates = {1: 1.0, 2: 0.8, 3: 0.5, 4: 0.2}
    return LinearEphemeris(epoch=timeline_epoch, base_longitudes=base, rates_deg_per_day=rates)

