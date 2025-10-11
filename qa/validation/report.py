"""Reporting helpers for cross-engine validation outputs.

This module persists cross-engine comparison artefacts and provides
hash-based verification for the Solar Fire parity reports committed to
the repository.  The hashes are treated as governance evidence:
automation checks them in CI whenever detector-affecting code paths
change, ensuring the stored Solar Fire comparisons continue to match
their recorded expectations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .cross_engine import MatrixResult, render_markdown, write_report_json

__all__ = [
    "HashCheckResult",
    "check_solarfire_hashes",
    "compare_expected_hashes",
    "compute_sha256",
    "load_hash_expectations",
    "write_artifacts",
]

_DEFAULT_SOLARFIRE_ROOT = Path(__file__).resolve().parents[1] / "artifacts" / "solarfire"
_DEFAULT_EXPECTATIONS = _DEFAULT_SOLARFIRE_ROOT / "expectations.json"


@dataclass(frozen=True)
class HashCheckResult:
    """Outcome of verifying artefact hashes against expectations."""

    computed: Mapping[str, str]
    missing: tuple[str, ...]
    mismatched: Mapping[str, tuple[str | None, str | None]]

    @property
    def ok(self) -> bool:
        """Return ``True`` when no missing files or mismatches were detected."""

        return not self.missing and not self.mismatched


def write_artifacts(result: MatrixResult, directory: Path) -> None:
    """Persist JSON + Markdown reports into ``directory``."""

    directory.mkdir(parents=True, exist_ok=True)
    write_report_json(result, directory / "cross_engine.json")
    render_markdown(result, directory / "cross_engine.md")


def compute_sha256(path: Path) -> str:
    """Return the SHA-256 hash for ``path``.

    The helper streams the file to avoid loading the entire artefact into
    memory, ensuring parity with the ``sha256sum`` command documented in
    Solar Fire provenance notes.
    """

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_hash_expectations(path: Path = _DEFAULT_EXPECTATIONS) -> dict[str, str]:
    """Load expected hashes from ``path``.

    The JSON structure is ``{"artifacts": {"relative/path": "sha256"}}``;
    the outer ``artifacts`` key is optional for backwards compatibility.
    """

    payload = json.loads(path.read_text())
    if isinstance(payload, dict) and "artifacts" in payload:
        mapping = payload["artifacts"]
    else:
        mapping = payload

    if not isinstance(mapping, Mapping):  # pragma: no cover - defensive
        raise TypeError("expected mapping of artifact paths to hashes")

    normalized: dict[str, str] = {}
    for rel_path, digest in mapping.items():
        if not isinstance(rel_path, str) or not isinstance(digest, str):
            raise TypeError("hash expectations must map strings to strings")
        normalized[rel_path] = digest.lower()
    return normalized


def compare_expected_hashes(
    expectations: Mapping[str, str],
    root: Path,
) -> HashCheckResult:
    """Compare ``expectations`` against artefacts stored under ``root``."""

    computed: dict[str, str] = {}
    missing: list[str] = []
    mismatched: dict[str, tuple[str | None, str | None]] = {}

    for rel_path, expected_digest in sorted(expectations.items()):
        artifact_path = root / rel_path
        if not artifact_path.exists():
            missing.append(rel_path)
            mismatched[rel_path] = (expected_digest, None)
            continue
        actual_digest = compute_sha256(artifact_path)
        computed[rel_path] = actual_digest
        if actual_digest.lower() != expected_digest.lower():
            mismatched[rel_path] = (expected_digest, actual_digest)

    return HashCheckResult(
        computed=computed,
        missing=tuple(missing),
        mismatched=mismatched,
    )


def check_solarfire_hashes(
    expectations_path: Path = _DEFAULT_EXPECTATIONS,
    artifacts_root: Path = _DEFAULT_SOLARFIRE_ROOT,
) -> HashCheckResult:
    """Verify Solar Fire comparison reports against recorded expectations."""

    expectations = load_hash_expectations(expectations_path)
    return compare_expected_hashes(expectations, artifacts_root)


def _command_check_solarfire(args: argparse.Namespace) -> int:
    result = check_solarfire_hashes(args.expectations, args.artifacts_root)

    if result.ok:
        for rel_path, digest in sorted(result.computed.items()):
            print(f"{rel_path}: {digest}")
        return 0

    if result.missing:
        print("Missing artefacts:")
        for rel_path in result.missing:
            expected, _ = result.mismatched.get(rel_path, (None, None))
            print(f"  - {rel_path} (expected {expected})")

    mismatches = {
        key: value
        for key, value in result.mismatched.items()
        if value[1] is not None and value[0] != value[1]
    }
    if mismatches:
        print("Hash mismatches:")
        for rel_path, (expected, actual) in sorted(mismatches.items()):
            print(f"  - {rel_path}")
            print(f"      expected: {expected}")
            print(f"      actual:   {actual}")

    return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")

    check_parser = subparsers.add_parser(
        "check-solarfire",
        help="Verify Solar Fire comparison artefacts using stored hashes.",
    )
    check_parser.add_argument(
        "--expectations",
        type=Path,
        default=_DEFAULT_EXPECTATIONS,
        help="Path to the Solar Fire hash expectations JSON file.",
    )
    check_parser.add_argument(
        "--artifacts-root",
        type=Path,
        default=_DEFAULT_SOLARFIRE_ROOT,
        help="Directory containing Solar Fire comparison artefacts.",
    )
    check_parser.set_defaults(func=_command_check_solarfire)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point used by ``python -m qa.validation.report``."""

    parser = _build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover - exercise via CLI
    raise SystemExit(main())
