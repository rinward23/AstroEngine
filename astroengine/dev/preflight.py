# >>> AUTO-GEN BEGIN: Transit Preflight v1.1
from __future__ import annotations

import ast
import difflib
import hashlib
import os
import re
from dataclasses import dataclass
from typing import Optional, Tuple

AUTOGEN_BEGIN = "# >>> AUTO-GEN BEGIN: {name}"
AUTOGEN_END = "# >>> AUTO-GEN END: {name}"


# ---------- Helpers ----------

def _read(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _write_atomic(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)
    os.replace(tmp_path, path)


def sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


# ---------- Symbol introspection ----------

def has_class(path: str, class_name: str) -> bool:
    source = _read(path)
    if not source:
        return False
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    return any(isinstance(node, ast.ClassDef) and node.name == class_name for node in tree.body)


def has_function(path: str, func_name: str) -> bool:
    source = _read(path)
    if not source:
        return False
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    return any(isinstance(node, ast.FunctionDef) and node.name == func_name for node in tree.body)


def export_exists(init_path: str, symbol: str) -> bool:
    """Detect direct imports or __all__ entries for `symbol`."""

    source = _read(init_path)
    if not source:
        return False
    if f"{symbol}" in source and ("__all__" in source or "from ." in source or "from astroengine." in source):
        return True
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = [getattr(target, "id", None) for target in node.targets]
            if "__all__" in targets:
                values = getattr(node.value, "elts", [])
                if any(getattr(value, "value", None) == symbol for value in values):
                    return True
    return False


# ---------- Auto-gen block upsert ----------

def upsert_autogen_block(path: str, name: str, new_block: str) -> Tuple[str, str, bool]:
    """Ensure a named AUTO-GEN block matches `new_block`.

    Returns (old_content, new_content, changed?). Creates file when missing.
    """

    begin = AUTOGEN_BEGIN.format(name=name)
    end = AUTOGEN_END.format(name=name)
    current = _read(path)

    block = f"{begin}\n{new_block.rstrip()}\n{end}\n"

    if not current:
        return "", block, True

    if begin in current and end in current:
        prefix, remainder = current.split(begin, 1)
        inside, suffix = remainder.split(end, 1)
        existing_block = f"{begin}{inside}{end}"
        desired_block = block.strip("\n")
        if existing_block.strip("\n") == desired_block:
            return current, current, False
        new_source = f"{prefix}{block}{suffix}"
        return current, new_source, True

    new_source = current + ("\n\n" if not current.endswith("\n") else "") + block
    return current, new_source, True


# ---------- YAML ruleset helpers ----------

def _find_module_ids(source: str) -> list[str]:
    pattern = re.compile(r"^\s*-\s+id:\s*(?P<id>[^\s#]+)", re.MULTILINE)
    return [match.group("id") for match in pattern.finditer(source or "")]


def ruleset_has_module(path: str, module_id: str) -> bool:
    source = _read(path)
    if not source:
        return False
    return module_id in _find_module_ids(source)


def _extract_module_id(module_yaml: str) -> Optional[str]:
    ids = _find_module_ids(module_yaml)
    if ids:
        return ids[0]
    pattern = re.compile(r"^\s*id:\s*(?P<id>[^\s#]+)", re.MULTILINE)
    match = pattern.search(module_yaml)
    return match.group("id") if match else None


def add_ruleset_module_if_missing(path: str, module_block_yaml: str) -> Tuple[str, str, bool]:
    """Append `module_block_yaml` under modules when absent."""

    source = _read(path)
    if not source:
        content = module_block_yaml if module_block_yaml.endswith("\n") else module_block_yaml + "\n"
        return "", content, True
    module_id = _extract_module_id(module_block_yaml)
    if module_id and ruleset_has_module(path, module_id):
        return source, source, False
    new_source = source.rstrip() + "\n\n" + module_block_yaml.rstrip() + "\n"
    return source, new_source, True


# ---------- Reporting ----------


def preview_diff(old: str, new: str, path: str) -> str:
    if old == new:
        return ""
    diff = difflib.unified_diff(
        old.splitlines(True), new.splitlines(True), fromfile=f"a/{path}", tofile=f"b/{path}"
    )
    return "".join(diff)


@dataclass
class PreflightReport:
    actions: list[str]
    skipped: list[str]
    diffs: list[str]

    def is_clean(self) -> bool:
        return not self.actions


def apply_if_changed(path: str, old: str, new: str, report: PreflightReport) -> None:
    if old == new:
        report.skipped.append(f"unchanged: {path}")
        return
    report.actions.append(f"write: {path}")
    diff = preview_diff(old, new, path)
    if diff:
        report.diffs.append(diff)
    _write_atomic(path, new)


# ---------- Repository-specific recipes ----------

def preflight_transit_engine(repo_root: str) -> PreflightReport:
    """Apply idempotent updates for the transit engine API + exports + ruleset wiring."""

    report = PreflightReport(actions=[], skipped=[], diffs=[])

    api_path = os.path.join(repo_root, "src", "astroengine", "transit", "api.py")
    block_name = "TransitAPI v0.1"
    block_code = """from dataclasses import dataclass\nfrom typing import Iterable, Literal, Optional, Sequence\n\nAspectName = Literal[\n    \"conjunction\",\"opposition\",\"square\",\"trine\",\"sextile\",\n    \"quincunx\",\"semisextile\",\"semisquare\",\"sesquisquare\"\n]\n\n@dataclass\nclass TransitScanConfig:\n    natal_id: str\n    start_iso: str\n    end_iso: str\n    step: str = \"1h\"\n    aspects: Sequence[AspectName] = (\"conjunction\",\"opposition\",\"square\",\"trine\",\"sextile\")\n    include_declination: bool = False\n    include_antiscia: bool = False\n    topocentric: bool = False\n    site_lat: Optional[float] = None\n    site_lon: Optional[float] = None\n    site_elev_m: float = 0.0\n    ephemeris_profile: str = \"default\"\n    orb_policy: str = \"default\"\n    severity_profile: str = \"standard\"\n    family_cap_per_day: int = 3\n\n@dataclass\nclass TransitEvent:\n    t_exact: str\n    t_applying: bool\n    partile: bool\n    aspect: AspectName\n    transiting_body: str\n    natal_point: str\n    orb_deg: float\n    severity: float\n    family: str\n    lon_transit: float\n    lon_natal: float\n    decl_transit: Optional[float] = None\n    notes: Optional[str] = None\n\nclass TransitEngine:\n    def __init__(self, engine_config): ...\n    def scan(self, cfg: TransitScanConfig) -> Iterable[TransitEvent]: ...\n"""

    old_api, new_api, _changed_api = upsert_autogen_block(api_path, block_name, block_code)
    apply_if_changed(api_path, old_api, new_api, report)

    init_path = os.path.join(repo_root, "src", "astroengine", "__init__.py")
    init_source = _read(init_path)
    ensure_line = "from .transit.api import TransitEngine, TransitScanConfig\n"
    if ensure_line not in init_source:
        updated = init_source + ("\n" if not init_source.endswith("\n") else "") + ensure_line
        apply_if_changed(init_path, init_source, updated, report)
    else:
        report.skipped.append("export exists: astroengine.__init__.py")

    ruleset_path = os.path.join(repo_root, "rulesets", "vca_astroengine_master.yaml")
    module_yaml = """
modules:
  - id: transit.scan
    channels:
      ingest: { group: natal }
      process:
        provider: skyfield_default
        step: 1h
        aspects: [conjunction, opposition, square, trine, sextile]
        options:
          include_declination: true
          include_antiscia: false
      gate: |
        family_cap_per_day(3) and (
          (aspect in [conjunction, opposition, square] and severity >= 0.65) or
          (aspect in [trine, sextile] and transiting_body in [Jupiter, Venus])
        )
      score: { profile: standard }
      export: { sqlite: data/transits.db }
"""
    old_ruleset, new_ruleset, _changed_ruleset = add_ruleset_module_if_missing(ruleset_path, module_yaml)
    apply_if_changed(ruleset_path, old_ruleset, new_ruleset, report)

    return report


__all__ = [
    "AUTOGEN_BEGIN",
    "AUTOGEN_END",
    "PreflightReport",
    "add_ruleset_module_if_missing",
    "apply_if_changed",
    "export_exists",
    "has_class",
    "has_function",
    "preflight_transit_engine",
    "preview_diff",
    "ruleset_has_module",
    "sha256",
    "upsert_autogen_block",
]
# >>> AUTO-GEN END: Transit Preflight v1.1
