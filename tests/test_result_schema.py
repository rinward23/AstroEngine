from __future__ import annotations

from copy import deepcopy

import pytest

from astroengine.validation import SchemaValidationError, validate_payload


def _valid_result_payload() -> dict:
    return {
        "schema": {"id": "astroengine.result", "version": "v1.0.0"},
        "run": {
            "id": "RUN-AB12CD",
            "profile": "base",
            "generated_at": "2025-09-03T12:00:00Z",
            "engine_version": "0.2.0",
            "ruleset_version": "2025-09-03",
            "seed": 42,
            "timezone": "America/New_York",
        },
        "window": {
            "start": "2025-09-03T00:00:00Z",
            "end": "2025-09-04T00:00:00Z",
            "timezone": "America/New_York",
            "label": "Primary Window",
        },
        "subjects": [
            {
                "token": "USER_PRIMARY",
                "name": "Chris",
                "role": "primary",
                "id": "IND-001",
                "consent": True,
            }
        ],
        "channels": [
            {
                "id": "relationship",
                "name": "Relationship",
                "score": 42.5,
                "strength": 78.2,
                "state": "surging",
                "subchannels": [
                    {
                        "id": "relationship_bonding",
                        "name": "Bonding",
                        "score": 44.8,
                        "state": "peaking",
                        "peaks": [
                            {
                                "window_id": "2025-09-03",
                                "score": 45.5,
                                "timestamp": "2025-09-03T18:00:00Z",
                            }
                        ],
                    }
                ],
                "peaks": [
                    {
                        "window_id": "2025-09-03",
                        "score": 43.0,
                        "timestamp": "2025-09-03T18:00:00Z",
                        "tier": "major",
                    }
                ],
            }
        ],
        "events": [
            {
                "id": "EVT-0001",
                "datetime": "2025-09-03T17:45:00Z",
                "window_id": "2025-09-03",
                "window_label": "2025-09-03",
                "layer": "transits",
                "subject": "USER_PRIMARY",
                "body": "Venus",
                "aspect": "trine",
                "target": "Mars",
                "channel": "relationship",
                "orb": 1.2,
                "valence": 0.85,
                "strength": 72.5,
                "confidence": 0.92,
                "time_bin": "afternoon",
                "day_tilt": "rising",
                "window_type": "peak",
                "strength_bin": "high",
                "impact_axes": ["relationship", "creativity"],
                "intent_hint": "connect",
                "channel_state": "surging",
                "is_major_event": True,
                "impact_flags": ["primary"],
                "is_angular": False,
                "is_sensitive_degree": True,
                "is_declination_hit": False,
                "contributes_to_peak": True,
                "is_near_threshold": False,
                "tags": ["Venus", "Mars", "trine"],
                "notes": "Favorable connection",
            }
        ],
    }


def test_result_schema_accepts_valid_payload():
    payload = _valid_result_payload()
    validate_payload("result_v1", payload)


def test_result_schema_rejects_invalid_event_payload():
    payload = _valid_result_payload()
    broken = deepcopy(payload)
    broken["events"][0].pop("channel")
    with pytest.raises(SchemaValidationError):
        validate_payload("result_v1", broken)


def _shadow_period_payload() -> dict:
    return {
        "ts": "2024-08-15T04:20:00Z",
        "jd": 2460523.68056,
        "body": "mercury",
        "kind": "pre",
        "end_ts": "2024-09-09T15:10:00Z",
        "end_jd": 2460549.13008,
        "retrograde_station_ts": "2024-09-09T15:10:00Z",
        "retrograde_station_jd": 2460549.13008,
        "retrograde_longitude": 206.347,
        "direct_station_ts": "2024-10-02T01:45:00Z",
        "direct_station_jd": 2460571.57361,
        "direct_longitude": 182.912,
        "start_longitude": 198.5,
        "end_longitude": 206.347,
    }


def _house_ingress_payload() -> dict:
    return {
        "ts": "2024-03-21T05:12:00Z",
        "jd": 2460386.71736,
        "body": "sun",
        "longitude": 0.015,
        "from_sign": "House 12",
        "to_sign": "House 1",
        "sign": "House 1",
        "motion": "direct",
        "retrograde": False,
        "speed_longitude": 0.9856,
        "speed_deg_per_day": 0.9856,
    }


def test_shadow_period_schema_accepts_valid_payload():
    payload = _shadow_period_payload()
    validate_payload("shadow_period_event_v1", payload)


def test_shadow_period_schema_rejects_invalid_kind():
    payload = deepcopy(_shadow_period_payload())
    payload["kind"] = "during"
    with pytest.raises(SchemaValidationError):
        validate_payload("shadow_period_event_v1", payload)


def test_house_ingress_schema_accepts_valid_payload():
    payload = _house_ingress_payload()
    validate_payload("house_ingress_event_v1", payload)


def test_house_ingress_schema_rejects_invalid_house_label():
    payload = deepcopy(_house_ingress_payload())
    payload["from_sign"] = "Aries"
    with pytest.raises(SchemaValidationError):
        validate_payload("house_ingress_event_v1", payload)
