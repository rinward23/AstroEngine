#!/usr/bin/env python3
"""Generate docs/COMPATIBILITY_MATRIX.md from the runtime registry."""

from __future__ import annotations

from collections.abc import Iterable
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from astroengine.modules import DEFAULT_REGISTRY
 
DOC_PATH = ROOT / "docs" / "COMPATIBILITY_MATRIX.md"
INSTRUCTIONS = """<!-- >>> AUTO-GEN BEGIN: Compatibility Matrix v1.0 (instructions) -->\nMatrix columns:\n- astroengine-core, rulesets, profiles, providers(skyfield/swe), exporters, fixed-stars data.\nPolicy:\n- Update on every tagged release; CI checks matrix completeness.\n<!-- >>> AUTO-GEN END: Compatibility Matrix v1.0 (instructions) -->"""

PROFILE_RE = re.compile(r"profiles/[\w./-]+")
RULESET_RE = re.compile(r"rulesets/[\w./-]+")
SCHEMA_RE = re.compile(r"schemas/[\w./-]+")
DATASET_RE = re.compile(r"datasets/[\w./-]+")
EXPORTER_RE = re.compile(r"astroengine\.exporters[\w.]*")

DATASET_NOTES: dict[str, str] = {
    "profiles/base_profile.yaml": "profiles/base_profile.yaml v0.1.0 (schema 1, updated 2024-05-01)",
    "profiles/dignities.csv": "profiles/dignities.csv (Solar Fire ESSENTIAL.DAT parity)",
    "profiles/fixed_stars.csv": "profiles/fixed_stars.csv (FK6/HYG v4.1, J2000)",
    "profiles/vca_outline.json": "profiles/vca_outline.json v2025-09-18",
    "profiles/aspects_policy.json": "profiles/aspects_policy.json (AE Aspects Policy v1.1)",
    "profiles/domains/chinese.yaml": "profiles/domains/chinese.yaml (BaZi/Zi Wei provenance)",
    "rulesets/transit/stations.ruleset.md": "rulesets/transit/stations.ruleset.md (schema transit_station)",
    "rulesets/transit/ingresses.ruleset.md": "rulesets/transit/ingresses.ruleset.md (schema transit_ingress)",
    "rulesets/transit/lunations.ruleset.md": "rulesets/transit/lunations.ruleset.md (schema transit_lunation)",
    "rulesets/transit/scan.ruleset.md": "rulesets/transit/scan.ruleset.md (schema transit_event)",
    "schemas/orbs_policy.json": "schemas/orbs_policy.json v2025-09-03",
    "schemas/contact_gate_schema_v2.json": "schemas/contact_gate_schema_v2.json",
    "schemas/natal_input_v1_ext.json": "schemas/natal_input_v1_ext.json",
    "schemas/result_schema_v1.json": "schemas/result_schema_v1.json",
    "schemas/result_schema_v1_with_domains.json": "schemas/result_schema_v1_with_domains.json",
    "datasets/star_names_iau.csv": "datasets/star_names_iau.csv (IAU WGSN v2024-03)",
}

PROVIDER_LABELS = {
    "Swiss Ephemeris": "Swiss Ephemeris",
    "Skyfield": "Skyfield",
}

FIXED_STAR_HINTS = ("fixed_star", "star_names")


def iter_strings(obj: object) -> Iterable[str]:
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for value in obj.values():
            yield from iter_strings(value)
    elif isinstance(obj, Iterable):
        for item in obj:
            yield from iter_strings(item)


def _extract_matches(text: str, pattern: re.Pattern[str]) -> list[str]:
    return pattern.findall(text)


def _collect_assets(strings: list[str]) -> tuple[set[str], set[str], set[str], set[str]]:
    rulesets: set[str] = set()
    profiles: set[str] = set()
    datasets: set[str] = set()
    exporters: set[str] = set()
    for raw in strings:
        if not isinstance(raw, str):
            continue
        for match in _extract_matches(raw, RULESET_RE):
            rulesets.add(match)
        for match in _extract_matches(raw, SCHEMA_RE):
            rulesets.add(match)
        for match in _extract_matches(raw, PROFILE_RE):
            profiles.add(match)
        for match in _extract_matches(raw, DATASET_RE):
            datasets.add(match)
        for match in _extract_matches(raw, EXPORTER_RE):
            exporters.add(match)
        if raw.startswith("profiles/"):
            profiles.add(raw)
        if raw.startswith("rulesets/") or raw.startswith("schemas/"):
            rulesets.add(raw)
        if raw.startswith("datasets/"):
            datasets.add(raw)
    return rulesets, profiles, datasets, exporters


def _collect_providers(strings: list[str]) -> list[str]:
    providers: set[str] = set()
    for raw in strings:
        if not isinstance(raw, str):
            continue
        lowered = raw.lower()
        for needle, label in PROVIDER_LABELS.items():
            if needle.lower() in lowered:
                providers.add(label)
    return sorted(providers)


def _collect_fixed_star_assets(paths: set[str]) -> list[str]:
    assets: set[str] = set()
    for path in paths:
        lowered = path.lower()
        if any(hint in lowered for hint in FIXED_STAR_HINTS):
            assets.add(path)
    return sorted(assets)


def _format_cells(items: list[str]) -> str:
    if not items:
        return "—"
    return "<br>".join(items)


def _annotate_paths(paths: Iterable[str]) -> list[str]:
    annotated: list[str] = []
    for path in sorted(paths):
        annotated.append(DATASET_NOTES.get(path, path))
    return annotated


def main() -> None:
    snapshot = DEFAULT_REGISTRY.as_dict()
    rows: list[tuple[str, str, str, list[str], list[str], list[str], list[str], list[str]]] = []
    for module_name, module in snapshot.items():
        for submodule_name, submodule in module["submodules"].items():
            for channel_name, channel in submodule["channels"].items():
                strings: list[str] = []
                strings.extend(iter_strings(module["metadata"]))
                strings.extend(iter_strings(submodule["metadata"]))
                strings.extend(iter_strings(channel["metadata"]))
                for subchannel in channel["subchannels"].values():
                    strings.extend(iter_strings(subchannel))
                rulesets, profiles, datasets, exporters = _collect_assets(strings)
                providers = _collect_providers(strings)
                fixed_star_assets = _collect_fixed_star_assets(profiles | datasets)
                rows.append(
                    (
                        module_name,
                        submodule_name,
                        channel_name,
                        _annotate_paths(rulesets),
                        _annotate_paths(profiles),
                        providers,
                        sorted(exporters),
                        _annotate_paths(fixed_star_assets),
                    )
                )
    rows.sort(key=lambda item: (item[0], item[1], item[2]))

    header = [
        "| Module | Submodule | Channel | Rulesets / Schemas | Profiles | Providers (Skyfield/SWE) | Exporters | Fixed-star datasets |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    body: list[str] = []
    for module_name, submodule_name, channel_name, rulesets, profiles, providers, exporters, fixed_star in rows:
        body.append(
            "| {module} | {submodule} | {channel} | {rulesets} | {profiles} | {providers} | {exporters} | {fixed_star} |".format(
                module=module_name,
                submodule=submodule_name,
                channel=channel_name,
                rulesets=_format_cells(rulesets),
                profiles=_format_cells(profiles),
                providers=_format_cells(providers),
                exporters=_format_cells(exporters),
                fixed_star=_format_cells(fixed_star),
            )
        )

    DOC_PATH.write_text(INSTRUCTIONS + "\n\n" + "\n".join(header + body) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
