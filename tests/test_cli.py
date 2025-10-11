import io
import json
import sys
import hashlib
from pathlib import Path
from types import SimpleNamespace

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
        "--target-frame",
        "natal",
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
    monkeypatch.setenv(
        "ASTROENGINE_SCAN_ENTRYPOINTS", "tests.fixtures.stub_scan:fake_scan"
    )
    json_path = tmp_path / "scan.json"
    ics_path = tmp_path / "scan.ics"
    sqlite_path = tmp_path / "scan.db"
    parquet_path = tmp_path / "scan.parquet"
    canonical_sqlite_path = tmp_path / "canonical.db"
    canonical_parquet_path = tmp_path / "canonical.parquet"

    from astroengine.cli.channels.transit import scan as scan_mod
    from astroengine.cli.channels.transit import exports as exports_mod

    def fake_parquet(path: str, events):
        records = list(events)
        payload = f"{Path(path).name}:{len(records)}".encode("utf-8")
        Path(path).write_bytes(payload)
        return len(records)

    monkeypatch.setattr(scan_mod, "write_parquet_canonical", fake_parquet)
    monkeypatch.setattr(exports_mod, "write_parquet_canonical", fake_parquet)

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
        "--profile",
        "integration",
        "--export-json",
        str(json_path),
        "--export-ics",
        str(ics_path),
        "--export-sqlite",
        str(sqlite_path),
        "--export-parquet",
        str(parquet_path),
        "--sqlite",
        str(canonical_sqlite_path),
        "--parquet",
        str(canonical_parquet_path),
        "--step-minutes",
        "90",
    ]

    exit_code = cli.main(args)
    assert exit_code == 0
    payload = json.loads(json_path.read_text())
    assert isinstance(payload, list)
    assert payload[0]["moving"]
    assert "BEGIN:VCALENDAR" in ics_path.read_text()

    def _manifest_for(path: Path) -> dict:
        manifest_path = path.with_name(path.name + ".manifest.json")
        return json.loads(manifest_path.read_text())

    ics_manifest = _manifest_for(ics_path)
    sqlite_manifest = _manifest_for(sqlite_path)
    parquet_manifest = _manifest_for(parquet_path)
    canonical_sqlite_manifest = _manifest_for(canonical_sqlite_path)
    canonical_parquet_manifest = _manifest_for(canonical_parquet_path)

    expected_start = "2024-01-01T00:00:00Z"
    expected_end = "2024-01-02T00:00:00Z"
    for manifest in (
        ics_manifest,
        sqlite_manifest,
        parquet_manifest,
        canonical_sqlite_manifest,
        canonical_parquet_manifest,
    ):
        assert manifest["schema"]["id"] == "astroengine.export.manifest"
        assert manifest["scan_window"] == {"start": expected_start, "end": expected_end}
        assert manifest["meta"]["event_count"] == 2
        assert manifest["meta"]["provider"] == "auto"
        assert "tests.fixtures.stub_scan.fake_scan" == manifest["meta"]["entrypoint"]
        assert set(manifest["profile_ids"]) >= {"default", "integration"}

    ics_checksum = hashlib.sha256(ics_path.read_bytes()).hexdigest()
    assert ics_manifest["outputs"][0]["checksum"]["sha256"] == ics_checksum
    assert sqlite_manifest["outputs"][0]["rows"] == 2
    assert canonical_sqlite_manifest["outputs"][0]["rows"] == 2
    assert parquet_manifest["outputs"][0]["checksum"]["sha256"] == hashlib.sha256(
        parquet_path.read_bytes()
    ).hexdigest()
    assert canonical_parquet_manifest["outputs"][0]["checksum"]["sha256"] == hashlib.sha256(
        canonical_parquet_path.read_bytes()
    ).hexdigest()


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


def test_cli_export_handles_large_jsonl(tmp_path, monkeypatch):
    from astroengine.cli import export as export_mod

    jsonl_path = tmp_path / "events.jsonl"
    out_path = tmp_path / "events.parquet"

    events = [{"event_id": idx, "value": idx * 2} for idx in range(2048)]
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event) + "\n")

    captured: list[dict[str, object]] = []

    def fake_export(path: str, stream):
        assert path == str(out_path)
        rows = list(stream)
        captured.extend(rows)
        Path(path).write_text(json.dumps(rows), encoding="utf-8")
        return len(rows)

    monkeypatch.setattr(export_mod, "export_parquet_dataset", fake_export)

    args = SimpleNamespace(
        input=str(jsonl_path),
        out=str(out_path),
        format="jsonl",
        key=None,
        multiwheel_spec=None,
        multiwheel_out=None,
        multiwheel_format="svg",
    )

    exit_code = export_mod.run(args)
    assert exit_code == 0
    assert len(captured) == len(events)
    assert captured[0]["event_id"] == 0
    assert captured[-1]["value"] == (len(events) - 1) * 2

    manifest_path = out_path.with_name(out_path.name + ".manifest.json")
    assert manifest_path.exists()


def test_cli_export_emits_manifest(tmp_path, monkeypatch):
    from astroengine.cli import export as export_mod

    jsonl_path = tmp_path / "events.jsonl"
    out_path = tmp_path / "events.parquet"

    events = [
        {
            "event_id": "EVT-1",
            "profile_id": "alpha",
            "subject_ref": "SUB-1",
            "window": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-01-02T00:00:00Z",
            },
            "meta": {"provider": "swiss"},
        },
        {
            "event_id": "EVT-2",
            "profile_id": "alpha",
            "subject_ref": "SUB-1",
            "window": {
                "start": "2024-01-03T00:00:00Z",
                "end": "2024-01-04T00:00:00Z",
            },
            "meta": {"provider": "swiss"},
        },
    ]
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event) + "\n")

    def fake_export(path: str, stream):
        rows = list(stream)
        Path(path).write_text("payload", encoding="utf-8")
        return len(rows)

    monkeypatch.setattr(export_mod, "export_parquet_dataset", fake_export)

    args = SimpleNamespace(
        input=str(jsonl_path),
        out=str(out_path),
        format="jsonl",
        key=None,
        multiwheel_spec=None,
        multiwheel_out=None,
        multiwheel_format="svg",
    )

    exit_code = export_mod.run(args)
    assert exit_code == 0

    manifest_path = out_path.with_name(out_path.name + ".manifest.json")
    manifest = json.loads(manifest_path.read_text())
    assert manifest["schema"]["id"] == "astroengine.export.manifest"
    assert manifest["profile_ids"] == ["alpha"]
    assert manifest["natal_ids"] == ["SUB-1"]
    assert manifest["scan_window"] == {
        "start": "2024-01-01T00:00:00Z",
        "end": "2024-01-04T00:00:00Z",
    }
    assert manifest["meta"]["command"] == "export"
    assert manifest["meta"]["input_format"] == "jsonl"
    assert manifest["meta"]["event_count"] == 2
    assert manifest["meta"]["providers"] == ["swiss"]
    expected_checksum = hashlib.sha256(b"payload").hexdigest()
    output_entry = manifest["outputs"][0]
    assert output_entry["path"].endswith("events.parquet")
    assert output_entry["checksum"]["sha256"] == expected_checksum
    assert output_entry["rows"] == 2


def test_load_events_streams_stdin_jsonl(monkeypatch):
    from astroengine.cli import export as export_mod

    class NoReadStringIO(io.StringIO):
        def read(self, *args, **kwargs):  # pragma: no cover - defensive guard
            raise AssertionError("stream should be consumed lazily via iteration")

    payload = "\n".join(json.dumps({"index": idx}) for idx in range(3))
    fake_stdin = NoReadStringIO(payload)
    monkeypatch.setattr(
        export_mod,
        "sys",
        SimpleNamespace(stdin=fake_stdin, stderr=sys.stderr),
    )

    events = list(export_mod._load_events("-", "jsonl", None))
    assert [event["index"] for event in events] == [0, 1, 2]
    assert fake_stdin.tell() == len(payload)
