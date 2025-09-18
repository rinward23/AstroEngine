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
            "providers": {
                "ephemeris": {
                    "id": "astroengine.ephemeris.skyfield",
                    "name": "Skyfield Ephemeris",
                    "kind": "ephemeris",
                    "version": "2025.9",
                    "mode": "skyfield",
                    "ayanamsha": "tropical",
                    "house_system_default": "whole_sign",
                    "supports_minor_planets": True,
                    "supports_fixed_stars": True,
                    "supports_lunations": True,
                    "supports_eclipses": True,
                    "parity_window_arcsec": 1.2,
                    "house_cusp_tolerance_arcsec": 15.0,
                    "tests_ran": [
                        "sun_pluto_parity_window<2arcsec",
                        "placidus_vs_whole_sign_delta<0.5deg",
                    ],
                },
                "atlas": {
                    "id": "astroengine.atlas.tzdb",
                    "name": "TimezoneFinder Atlas",
                    "kind": "atlas",
                    "version": "2025.8",
                    "mode": "timezonefinder",
                    "supports_timezone_lookup": True,
                    "geocoder": "nominatim",
                },
                "fixed_stars": {
                    "id": "astroengine.catalog.fixedstars",
                    "name": "Fixed Star Catalog",
                    "kind": "fixed_star_catalog",
                    "version": "2025.8",
                    "mode": "catalog",
                    "epoch": "J2000.0",
                    "magnitude_limit": 2.0,
                },
                "time_scale": {
                    "id": "astroengine.time.tzdb",
                    "name": "IANA TZDB",
                    "kind": "time_scale",
                    "version": "2025a",
                    "mode": "tzdb",
                    "database": "tzdata",
                },
            },
            "ruleset_modules": [
                "transit.stations",
                "transit.ingresses",
                "transit.lunations",
                "transit.eclipses",
                "transit.combust",
                "transit.oob",
                "transit.declination",
                "transit.antiscia",
                "transit.midpoints",
                "transit.fixedstars",
            ],
            "extras": ["skyfield", "parquet"],
            "profile_settings": {
                "default_house_system": "whole_sign",
                "default_ayanamsha": "tropical",
                "enable_minor_planets": True,
                "enable_progressions": True,
                "enable_returns": True,
                "enable_fixed_stars": True,
                "enable_declination": True,
                "enable_midpoints": True,
                "enable_lunations": True,
                "enable_eclipses": True,
            },
            "data_integrity": {
                "datasets_verified": ["ephemeris_jpl", "fixed_star_catalog"],
                "ephemeris_cross_checks": [
                    "Sun-Pluto arcsecond parity < 2.0",
                    "Swiss Ephemeris parity verified",
                ],
                "house_system_checks": [
                    "Placidus vs Whole Sign cusp delta < 0.5°",
                ],
                "notes": "All integrity checks passed",
            },
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
                "natal": {
                    "timestamp": "1992-04-10T14:32:00Z",
                    "tzid": "America/New_York",
                    "utc_offset_minutes": -240,
                    "latitude": 40.7128,
                    "longitude": -74.006,
                    "altitude_m": 10.0,
                    "location_name": "New York, NY",
                    "source": "user_provided",
                    "atlas_provider": "timezonefinder",
                    "house_system": "whole_sign",
                    "ayanamsha": "tropical",
                    "notes": "Verified via tzdb",
                },
                "house_system": "whole_sign",
                "ayanamsha": "tropical",
                "data_sources": ["natal_index"],
            }
        ],
        "channels": [
            {
                "module": "transits",
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
                        "module": "transits",
                        "submodule": "transits.relationship",
                        "channel": "relationship",
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
                "submodule": "transits.relationship",
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
                "module": "transits",
                "submodule": "transits.relationship",
                "subchannel": "relationship_bonding",
                "family": "transit",
                "predicates": ["is_transit"],
                "feature_flags": {
                    "is_combust": False,
                    "is_under_beams": False,
                    "is_out_of_bounds": False,
                    "is_progressed": False,
                    "is_return": False,
                    "is_minor_planet": False,
                },
                "provenance": {
                    "dataset": "ephemeris_jpl",
                    "record_id": "VENUS-2025-09-03T17:45Z",
                    "source_module": "transits.core",
                    "calculation": "skyfield.ephemeris",
                    "timestamp": "2025-09-03T12:00:00Z",
                    "quality": "verified",
                },
                "house_system": "whole_sign",
                "ayanamsha": "tropical",
                "declination": 8.2,
                "progression_kind": "other",
                "return_kind": "other",
                "dataset_refs": ["ephemeris_jpl", "fixed_star_catalog"],
                "severity_modifier": 0.1,
            }
        ],
        "modules": [
            {
                "id": "transits",
                "name": "Transits Core",
                "description": "Primary transit scoring module",
                "profile": "AP-SUPER",
                "channels": [
                    {
                        "id": "relationship",
                        "name": "Relationship",
                        "description": "Relationship composite scoring",
                        "subchannels": [
                            {
                                "id": "relationship_bonding",
                                "name": "Bonding",
                                "description": "High-trust bonding focus",
                            }
                        ],
                    }
                ],
                "submodules": [
                    {
                        "id": "transits.relationship",
                        "name": "Relationship Focus",
                        "description": "Transits tuned to relationship channel",
                        "channels": [
                            {
                                "id": "relationship",
                                "name": "Relationship",
                                "description": "Relationship composite scoring",
                                "subchannels": [
                                    {
                                        "id": "relationship_bonding",
                                        "name": "Bonding",
                                        "description": "High-trust bonding focus",
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
        "datasets": [
            {
                "id": "ephemeris_jpl",
                "description": "JPL DE441 ephemeris subset",
                "format": "sqlite",
                "path": "db/ephemeris_jpl.sqlite",
                "indexed": True,
                "index_fields": ["jd"],
                "row_count": 123456,
                "checksum": "sha256:abc123",
                "last_updated": "2025-09-01T00:00:00Z",
            },
            {
                "id": "fixed_star_catalog",
                "description": "Curated fixed star table",
                "format": "csv",
                "path": "data/fixed_stars.csv",
                "indexed": True,
                "index_fields": ["name"],
                "row_count": 58,
                "checksum": "sha256:def456",
                "last_updated": "2025-08-20T00:00:00Z",
            },
        ],
    }


def test_result_schema_accepts_valid_payload():
    payload = _valid_result_payload()
    validate_payload("result_v1", payload)
    assert {
        "transit.stations",
        "transit.ingresses",
        "transit.lunations",
        "transit.eclipses",
        "transit.combust",
        "transit.oob",
        "transit.declination",
        "transit.antiscia",
        "transit.midpoints",
        "transit.fixedstars",
    }.issubset(set(payload["run"]["ruleset_modules"]))


def test_result_schema_rejects_invalid_event_payload():
    payload = _valid_result_payload()
    broken = deepcopy(payload)
    broken["events"][0].pop("channel")
    with pytest.raises(SchemaValidationError):
        validate_payload("result_v1", broken)
