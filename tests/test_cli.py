import json

from astroengine import cli


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


def test_cli_transits_runs(tmp_path):
    output = tmp_path / "events.json"
    args = [
        "transits",
        "--target-longitude",
        "240.9623186447056",
        "--start",
        "2025-10-20T00:00:00Z",
        "--end",
        "2025-11-20T00:00:00Z",
        "--json",
        str(output),
    ]
    cli.main(args)
    data = output.read_text()
    assert "timestamp" in data


def test_cli_validate_round_trip(tmp_path):
    payload = _valid_gate_payload()
    path = tmp_path / "payload.json"
    path.write_text(cli.json.dumps(payload))
    cli.main(["validate", "contact_gate_v2", str(path)])


def test_cli_scan_with_stub(tmp_path, monkeypatch):
    monkeypatch.setenv("ASTROENGINE_SCAN_ENTRYPOINTS", "tests.fixtures.stub_scan:fake_scan")
    json_path = tmp_path / "scan.json"
    ics_path = tmp_path / "scan.ics"
    sqlite_path = tmp_path / "scan.db"

    args = [
        "scan",
        "--start-utc",
        "2024-01-01T00:00:00Z",
        "--end-utc",
        "2024-01-02T00:00:00Z",
        "--moving",
        "Sun",
        "Mars",
        "--targets",
        "natal:Sun",
        "natal:Moon",
        "--target-frame",
        "natal",
        "--detector",
        "lunations",
        "--export-json",
        str(json_path),
        "--export-ics",
        str(ics_path),
        "--export-sqlite",
        str(sqlite_path),
        "--step-minutes",
        "90",
    ]

    exit_code = cli.main(args)
    assert exit_code == 0
    payload = json.loads(json_path.read_text())
    assert isinstance(payload, list)
    assert payload[0]["moving"]
    assert "BEGIN:VCALENDAR" in ics_path.read_text()


def test_cli_scan_parser_supports_sidereal():
    parser = cli.build_parser()
    ns = parser.parse_args(
        [
            "scan",
            "--start-utc",
            "2024-01-01T00:00:00Z",
            "--end-utc",
            "2024-01-02T00:00:00Z",
            "--sidereal",
            "--ayanamsha",
            "lahiri",
            "--detector",
            "lunations",
        ]
    )
    assert ns.command == "scan"
    assert ns.sidereal is True
    assert ns.ayanamsha == "lahiri"
    assert ns.detectors == ["lunations"]
