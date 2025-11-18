from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from astroengine import cli
from astroengine.developer_platform.webhooks import (
    InvalidSignatureError,
    SignatureExpiredError,
    compute_signature,
    verify_signature,
)
from astroengine.validation import SchemaValidationError, validate_payload

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "datasets" / "solarfire" / "jobs"


def _load_fixture(name: str) -> dict:
    path = FIXTURE_DIR / name
    return json.loads(path.read_text())


def _payload_bytes(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def test_job_delivery_schema_accepts_completed_fixture() -> None:
    payload = _load_fixture("job_delivery_completed.json")
    validate_payload("webhook_job_delivery_v1", payload)


def test_job_delivery_schema_rejects_missing_provenance() -> None:
    payload = deepcopy(_load_fixture("job_delivery_completed.json"))
    payload.pop("provenance", None)
    with pytest.raises(SchemaValidationError):
        validate_payload("webhook_job_delivery_v1", payload)


def test_verify_signature_accepts_valid_header() -> None:
    payload = _payload_bytes(_load_fixture("job_delivery_completed.json"))
    secret = "whsec_test"
    timestamp = 1_715_792_400
    header = f"t={timestamp}, v1={compute_signature(secret, timestamp, payload)}"
    verify_signature(payload, header, secret, now=timestamp, tolerance_seconds=600)


def test_verify_signature_rejects_bad_digest() -> None:
    payload = _payload_bytes(_load_fixture("job_delivery_completed.json"))
    secret = "whsec_test"
    timestamp = 1_715_792_400
    header = f"t={timestamp}, v1={'0' * 64}"
    with pytest.raises(InvalidSignatureError):
        verify_signature(payload, header, secret, now=timestamp)


def test_verify_signature_rejects_expired_timestamp() -> None:
    payload = _payload_bytes(_load_fixture("job_delivery_completed.json"))
    secret = "whsec_test"
    timestamp = 1_715_792_400
    header = f"t={timestamp}, v1={compute_signature(secret, timestamp, payload)}"
    with pytest.raises(SignatureExpiredError):
        verify_signature(payload, header, secret, tolerance_seconds=10, now=timestamp + 20)


def test_cli_webhooks_verify_success(tmp_path: Path) -> None:
    payload_mapping = _load_fixture("job_delivery_completed.json")
    payload_bytes = _payload_bytes(payload_mapping)
    payload_path = tmp_path / "payload.json"
    payload_path.write_bytes(payload_bytes)
    secret_path = tmp_path / "secret.txt"
    secret_path.write_text("whsec_cli", encoding="utf-8")
    timestamp = 1_715_792_400
    header = f"t={timestamp}, v1={compute_signature('whsec_cli', timestamp, payload_bytes)}"

    exit_code = cli.main(
        [
            "webhooks",
            "verify",
            "--payload-file",
            str(payload_path),
            "--secret-file",
            str(secret_path),
            "--signature-header",
            header,
            "--tolerance-seconds",
            "0",
        ]
    )
    assert exit_code == 0


def test_cli_webhooks_verify_failure(tmp_path: Path) -> None:
    payload_path = tmp_path / "payload.json"
    payload_path.write_bytes(_payload_bytes(_load_fixture("job_delivery_failed.json")))
    secret_path = tmp_path / "secret.txt"
    secret_path.write_text("whsec_cli", encoding="utf-8")
    header = "t=1, v1=deadbeef"

    exit_code = cli.main(
        [
            "webhooks",
            "verify",
            "--payload-file",
            str(payload_path),
            "--secret-file",
            str(secret_path),
            "--signature-header",
            header,
            "--tolerance-seconds",
            "0",
        ]
    )
    assert exit_code == 1
