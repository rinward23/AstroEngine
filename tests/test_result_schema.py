from __future__ import annotations

from copy import deepcopy

import pytest

from astroengine.validation import SchemaValidationError, validate_payload


def _valid_result_payload() -> dict:
    return {
        "schema": {"id": "astroengine.result", "version": "v1.0.0"},
        "run": {
            "id": "RUN-AB12CD",
            "profile": "AP-SUPER",
            "generated_at": "2025-09-03T12:00:00Z",
            "engine_version": "2025.9",
            "ruleset_version": "v2.18.13",
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
