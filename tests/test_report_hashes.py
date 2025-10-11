from __future__ import annotations

import hashlib
import json

import pytest

from qa.validation.report import (
    HashCheckResult,
    check_solarfire_hashes,
    compare_expected_hashes,
    compute_sha256,
    load_hash_expectations,
)


@pytest.mark.parametrize(
    "content",
    ["hello", "Solar Fire"],
)
def test_compute_sha256_matches_hashlib(tmp_path, content):
    path = tmp_path / "sample.txt"
    path.write_text(content)
    expected = hashlib.sha256(content.encode()).hexdigest()
    assert compute_sha256(path) == expected


def test_compare_expected_hashes_detects_mismatch(tmp_path):
    root = tmp_path / "artifacts"
    root.mkdir()
    report = root / "report.md"
    report.write_text("baseline")

    expectations = {"report.md": compute_sha256(report)}
    result = compare_expected_hashes(expectations, root)
    assert isinstance(result, HashCheckResult)
    assert result.ok

    report.write_text("modified")
    mismatch = compare_expected_hashes(expectations, root)
    assert not mismatch.ok
    assert "report.md" in mismatch.mismatched
    expected_digest, actual_digest = mismatch.mismatched["report.md"]
    assert expected_digest == expectations["report.md"]
    assert actual_digest == compute_sha256(report)


def test_check_solarfire_hashes_uses_expectations_file(tmp_path):
    artifacts_root = tmp_path / "solarfire"
    target_dir = artifacts_root / "2025-10-02"
    target_dir.mkdir(parents=True)

    artefact = target_dir / "cross_engine.json"
    artefact.write_text("{}\n")
    digest = compute_sha256(artefact)

    expectations_path = tmp_path / "expectations.json"
    expectations = {
        "version": 1,
        "artifacts": {"2025-10-02/cross_engine.json": digest},
    }
    expectations_path.write_text(json.dumps(expectations))

    result = check_solarfire_hashes(expectations_path, artifacts_root)
    assert result.ok
    assert result.computed["2025-10-02/cross_engine.json"] == digest


def test_load_hash_expectations_flat_structure(tmp_path):
    expectations_path = tmp_path / "expectations.json"
    payload = {"a.json": "abc123", "b.json": "DEF456"}
    expectations_path.write_text(json.dumps(payload))

    expectations = load_hash_expectations(expectations_path)
    assert expectations == {"a.json": "abc123", "b.json": "def456"}
