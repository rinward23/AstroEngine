from __future__ import annotations

import hashlib
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_ROOT = PROJECT_ROOT / "tests" / "golden" / "detectors"

SCENARIOS = (
    {
        "source": PROJECT_ROOT / "docs-site" / "docs" / "fixtures" / "timeline_events.json",
        "target": GOLDEN_ROOT / "timeline_mars_saturn.jsonl",
        "checksum": GOLDEN_ROOT / "timeline_mars_saturn.sha256",
    },
)


def _canonicalise(events: list[dict[str, object]]) -> list[str]:
    lines: list[str] = []
    for event in events:
        payload = {
            "angle_deg": event.get("angle_deg"),
            "family": event.get("family"),
            "kind": event.get("kind"),
            "moving": event.get("moving"),
            "orb_abs": event.get("orb_abs"),
            "target": event.get("target"),
            "ts": event.get("ts"),
        }
        lines.append(json.dumps(payload, sort_keys=True))
    lines.sort()
    return lines


def rebuild() -> None:
    GOLDEN_ROOT.mkdir(parents=True, exist_ok=True)
    for scenario in SCENARIOS:
        source_path = scenario["source"]
        target_path = scenario["target"]
        checksum_path = scenario["checksum"]

        events = json.loads(source_path.read_text(encoding="utf-8"))
        canonical_lines = _canonicalise(events)
        payload = "\n".join(canonical_lines) + "\n"

        target_path.write_text(payload, encoding="utf-8")
        checksum = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        checksum_path.write_text(checksum + "\n", encoding="utf-8")


if __name__ == "__main__":
    rebuild()
