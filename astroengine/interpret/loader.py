"""Rulepack loading utilities with validation and engine adapters."""

from __future__ import annotations


from dataclasses import dataclass
from pathlib import Path

from typing import Any, Generator, Mapping


import yaml
from jsonschema import Draft202012Validator


from .models import (
    ProfileDefinition,
    Rule,
    RuleThenRuntime,
    RuleWhen,
    Rulepack,
    RulepackDocument,
    RulepackLintResult,
)


class RulepackValidationError(Exception):
    """Raised when a rulepack fails schema or semantic validation."""

    def __init__(self, message: str, *, errors: list[dict[str, Any]] | None = None):
        super().__init__(message)
        self.errors = errors or []



@dataclass(frozen=True)
class LoadedRulepack:
    """Parsed rulepack document alongside its raw content and runtime view."""

    document: RulepackDocument
    content: dict[str, Any]
    runtime: Rulepack

    @property
    def rulepack(self) -> str:
        return self.runtime.id

    @property
    def profiles(self) -> dict[str, ProfileDefinition]:
        return self.runtime.profiles

    @property
    def rules(self) -> list[Rule]:
        return self.runtime.rules

    def profile_weights(self, profile: str) -> dict[str, float]:
        return self.runtime.profile_weights(profile)

    @property
    def archetypes(self) -> dict[str, list[str]]:
        return self.runtime.archetypes


    prepared = dict(data)
    meta = prepared.get("meta")
    meta_map = dict(meta) if isinstance(meta, Mapping) else {}
    rulepack_id = prepared.get("rulepack")
    if rulepack_id and "id" not in meta_map:
        meta_map["id"] = str(rulepack_id)
    if not rulepack_id and meta_map.get("id"):
        prepared["rulepack"] = str(meta_map["id"])
    if "name" not in meta_map and meta_map.get("title"):
        meta_map["name"] = str(meta_map["title"])
    if "title" not in meta_map and meta_map.get("name"):
        meta_map["title"] = str(meta_map["name"])
    if "version" not in prepared and "version" in meta_map:
        prepared["version"] = meta_map.get("version")
    if meta_map:
        prepared["meta"] = meta_map
    profiles = prepared.get("profiles")
    if isinstance(profiles, Mapping):
        normalized_profiles: dict[str, Any] = {}
        for name, payload in profiles.items():
            if not isinstance(payload, Mapping):
                normalized_profiles[str(name)] = payload
                continue
            profile_payload = dict(payload)
            if "tags" not in profile_payload and isinstance(
                profile_payload.get("tag_weights"), Mapping
            ):
                profile_payload["tags"] = dict(profile_payload["tag_weights"])
            normalized_profiles[str(name)] = profile_payload
        prepared["profiles"] = normalized_profiles
    return prepared



def _parse_raw(content: str, *, source: str | None = None) -> dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        try:
            parsed = yaml.safe_load(content)
        except yaml.YAMLError as exc:  # pragma: no cover - PyYAML handles wide input
            raise RulepackValidationError(
                f"failed to parse rulepack {source or ''}: {exc}"
            ) from exc
        if not isinstance(parsed, Mapping):
            raise RulepackValidationError("rulepack must be a JSON/YAML object")
        return dict(parsed)



def _build_runtime(document: RulepackDocument) -> Rulepack:
    rules: list[Rule] = []
    for rule_def in document.rules:
        cond = rule_def.when
        bodies_a = cond.bodiesA if cond.bodiesA is not None else "*"
        bodies_b = cond.bodiesB if cond.bodiesB is not None else "*"
        aspects = cond.aspects if cond.aspects is not None else "*"
        when = RuleWhen(
            bodiesA=bodies_a,
            bodiesB=bodies_b,
            aspects=aspects,
            min_severity=float(cond.min_severity or 0.0),
        )
        then = RuleThenRuntime(
            title=rule_def.then.title,
            tags=tuple(rule_def.then.tags),
            base_score=float(rule_def.then.base_score),
            score_fn=rule_def.then.score_fn,
            markdown_template=rule_def.then.markdown_template,
        )
        rules.append(Rule(id=rule_def.id, scope=rule_def.scope, when=when, then=then))
    return Rulepack(
        id=document.rulepack,
        version=int(document.version),
        profiles=document.profiles,
        archetypes=document.archetypes,
        rules=rules,
    )


def load_rulepack(raw: Any, *, source: str | None = None) -> LoadedRulepack:
    """Parse and validate a rulepack document from content or a filesystem path."""

    if isinstance(raw, Path):
        potential_path = raw
        if potential_path.exists() and potential_path.is_file():
            text = potential_path.read_text(encoding="utf-8")
            return load_rulepack(text, source=str(potential_path))
    elif isinstance(raw, str):
        stripped = raw.strip()
        # Treat as path only when it resembles a filesystem reference.
        if "\n" not in raw and not stripped.startswith("{") and not stripped.startswith("["):
            potential_path = Path(raw)
            if potential_path.exists() and potential_path.is_file():
                text = potential_path.read_text(encoding="utf-8")
                return load_rulepack(text, source=str(potential_path))
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    if isinstance(raw, str):
        content = _parse_raw(raw, source=source)
    elif isinstance(raw, Mapping):
        content = dict(raw)
    else:
        raise RulepackValidationError("rulepack payload must be string, bytes, mapping, or path")
    return load_rulepack_from_data(content, source=source)


def load_rulepack_from_data(data: Mapping[str, Any], *, source: str | None = None) -> LoadedRulepack:
    """Validate a pre-parsed rulepack mapping."""

    content = dict(data)
    errors: list[dict[str, Any]] = []
    for err in _VALIDATOR.iter_errors(content):
        errors.append(
            {
                "path": list(err.path),
                "message": err.message,
                "validator": err.validator,
            }

        )
    return rules



    runtime = _build_runtime(document)
    normalized = document.model_dump(mode="python")
    return LoadedRulepack(document=document, content=normalized, runtime=runtime)


    origin = source_name or source
    if isinstance(raw, Mapping):
        data = dict(raw)
        origin = origin or "<mapping>"
    elif isinstance(raw, (str, Path)):
        path_obj: Path | None = None
        try:
            path_obj = Path(raw)
        except (OSError, TypeError, ValueError):
            path_obj = None
        is_existing_path = False
        if path_obj is not None:
            try:
                is_existing_path = path_obj.exists()
            except OSError:
                is_existing_path = False
        if is_existing_path and path_obj is not None:
            origin = origin or str(path_obj)
            raw = path_obj.read_text(encoding="utf-8")
            data = _parse_raw(raw, source=origin)
        else:
            origin = origin or "<inline>"
            data = _parse_raw(str(raw), source=origin)
    elif isinstance(raw, bytes):
        origin = origin or "<bytes>"
        data = _parse_raw(raw.decode("utf-8"), source=origin)
    else:
        raise TypeError("unsupported rulepack input type")
    return load_rulepack_from_data(data, source=origin)


def load_rulepack_from_data(data: Mapping[str, Any], *, source: str | None = None) -> Rulepack:
    """Validate *data* against the rulepack schema and return a :class:`Rulepack`."""

    prepared = _prepare_for_validation(data)
    rules_raw = prepared.get("rules")
    new_style = False
    if isinstance(rules_raw, Iterable):
        for entry in rules_raw:
            if isinstance(entry, Mapping) and "then" in entry:
                new_style = True
                break
    if new_style:
        errors = [
            {
                "path": list(error.path),
                "message": error.message,
                "validator": error.validator,
            }
            for error in _VALIDATOR.iter_errors(prepared)
        ]
        if errors:
            raise RulepackValidationError("rulepack failed schema validation", errors=errors)
    return _build_rulepack(prepared)


def lint_rulepack(
    raw: str | bytes | Mapping[str, Any], *, source: str | None = None
) -> RulepackLintResult:
    """Return lint diagnostics for a rulepack payload without raising."""


    try:
        if isinstance(raw, Mapping):
            load_rulepack_from_data(raw, source=source)
        else:
            load_rulepack(raw, source=source)
    except RulepackValidationError as exc:
        return RulepackLintResult(ok=False, errors=exc.errors, warnings=[], meta={"source": source})
    return RulepackLintResult(ok=True, errors=[], warnings=[], meta={"source": source})



def iter_rulepack_rules(rulepack: Rulepack | LoadedRulepack) -> Generator[Rule, None, None]:
    """Yield rules from either a runtime rulepack or a loaded wrapper."""

    runtime = rulepack.runtime if isinstance(rulepack, LoadedRulepack) else rulepack
    for rule in runtime.rules:
        yield rule


__all__ = [
    "LoadedRulepack",
    "RulepackValidationError",

    "iter_rulepack_rules",
    "lint_rulepack",
    "load_rulepack",
    "load_rulepack_from_data",
]

