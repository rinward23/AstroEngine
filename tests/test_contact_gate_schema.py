from __future__ import annotations

from copy import deepcopy

import pytest

from astroengine.validation import SchemaValidationError, validate_payload


def _valid_gate_payload() -> dict:
    return {
        "schema": {"id": "astroengine.contact_gate", "version": "v2.0.0"},
        "run": {
            "id": "RUN-XY34ZT",
            "generated_at": "2025-09-03T12:05:00Z",
            "profile": "base",
            "ruleset_version": "2025-09-03",
        },
        "gates": [
            {
                "id": "GATE-001A",
                "channel": "relationship",
                "subchannel": "relationship_bonding",
                "decision": "include",
                "score": 42.0,
                "threshold": 35.0,
                "delta": 7.0,
                "window": {
                    "start": "2025-09-03T16:00:00Z",
                    "end": "2025-09-03T20:00:00Z",
                    "timezone": "America/New_York",
                    "label": "Transit Peak",
                },
                "subjects": [
                    {"token": "USER_PRIMARY", "role": "primary"},
                    {"token": "USER_SECONDARY", "role": "secondary"},
                ],
                "evidence": {
                    "summary": "Venus trine Mars near perfected peak",
                    "events": [
                        {
                            "event_id": "EVT-0001",
                            "orb": 1.2,
                            "valence": 0.85,
                            "strength": 72.5,
                            "near_threshold": False,
                        }
                    ],
                    "confidence": 0.93,
                    "notes": "Matches gating heuristics",
                },
                "audit": {
                    "decided_by": "astroengine.auto_gate",
                    "decided_at": "2025-09-03T12:05:01Z",
                    "source": "scoring.contact_gate",
                    "manual_override": False,
                },
                "recommendation": "Highlight in daily narrative",
            }
        ],
    }


def test_contact_gate_schema_accepts_valid_payload():
    payload = _valid_gate_payload()
    validate_payload("contact_gate_v2", payload)


def test_contact_gate_schema_rejects_bad_decision():
    payload = _valid_gate_payload()
    broken = deepcopy(payload)
    broken["gates"][0]["decision"] = "maybe"
    with pytest.raises(SchemaValidationError):
        validate_payload("contact_gate_v2", broken)
