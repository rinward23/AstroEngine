"""Rulepack loading utilities with validation and engine adapters."""

from __future__ import annotations


from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping

import json


import yaml
from jsonschema import Draft202012Validator

from astroengine.core.aspects_plus.harmonics import BASE_ASPECTS

from .models import Rule, RuleThen, RuleWhen, Rulepack, RulepackLintResult
from .schema import RULEPACK_SCHEMA



class RulepackValidationError(Exception):
    """Raised when a rulepack fails schema or semantic validation."""

    def __init__(self, message: str, *, errors: list[dict[str, Any]] | None = None):
        super().__init__(message)
        self.errors = errors or []



_VALIDATOR = Draft202012Validator(RULEPACK_SCHEMA)


def _prepare_for_validation(data: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy of *data* with required metadata fields populated."""

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



def _coerce_sequence(value: Any) -> tuple[str, ...] | str:
    if value == "*":
        return "*"
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Iterable):
        return tuple(str(item) for item in value)
    raise TypeError("expected string or iterable")


def _coerce_aspects(value: Any) -> tuple[int, ...] | str:
    if value in (None, "*"):
        return "*"
    items: Iterable[Any]
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        items = value
    else:
        items = (value,)
    resolved: list[int] = []
    for item in items:
        if isinstance(item, (int, float)) and not isinstance(item, bool):
            resolved.append(int(round(float(item))))
            continue
        angle = BASE_ASPECTS.get(str(item).lower())
        if angle is not None:
            resolved.append(int(round(float(angle))))
    return tuple(resolved) if resolved else "*"


def _coerce_profiles(data: Mapping[str, Any]) -> dict[str, dict[str, float]]:
    profiles: dict[str, dict[str, float]] = {}
    for name, payload in data.items():
        if not isinstance(payload, Mapping):
            raise RulepackValidationError(f"profile {name!r} must be a mapping")
        if "tags" in payload and isinstance(payload.get("tags"), Mapping):
            tags_map = payload.get("tags", {})
        elif "tag_weights" in payload and isinstance(payload.get("tag_weights"), Mapping):
            tags_map = payload.get("tag_weights", {})
        else:
            tags_map = {}
        base_multiplier = float(payload.get("base_multiplier", 1.0))
        profiles[str(name)] = {
            str(k): float(v) * base_multiplier for k, v in dict(tags_map).items()
        }
    return profiles


def _coerce_rules(entries: Iterable[Mapping[str, Any]]) -> list[Rule]:
    rules: list[Rule] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise RulepackValidationError("rules must contain mapping entries")
        when_payload = entry.get("when")
        if not isinstance(when_payload, Mapping):
            raise RulepackValidationError(f"rule {entry.get('id')} missing when block")
        then_payload = entry.get("then")
        if isinstance(then_payload, Mapping):
            bodies_a_raw = _coerce_sequence(when_payload.get("bodiesA", "*"))
            bodies_b_raw = _coerce_sequence(when_payload.get("bodiesB", "*"))
            aspects_raw = _coerce_aspects(when_payload.get("aspects", "*"))
            bodies_a = bodies_a_raw if bodies_a_raw == "*" else tuple(bodies_a_raw)
            bodies_b = bodies_b_raw if bodies_b_raw == "*" else tuple(bodies_b_raw)
            aspects = aspects_raw if aspects_raw == "*" else tuple(aspects_raw)
            min_sev = float(when_payload.get("min_severity", 0.0))
            when = RuleWhen(
                bodiesA=bodies_a,
                bodiesB=bodies_b,
                aspects=aspects,
                min_severity=min_sev,
            )
            tags = then_payload.get("tags")
            if not isinstance(tags, Iterable) or isinstance(tags, (str, bytes)):
                raise RulepackValidationError(f"rule {entry.get('id')} has invalid tags")
            then = RuleThen(
                title=str(then_payload.get("title", "")),
                tags=tuple(str(tag) for tag in tags),
                base_score=float(then_payload.get("base_score", 0.5)),
                score_fn=str(then_payload.get("score_fn", "cosine^1.0")),
                markdown_template=(
                    str(then_payload["markdown_template"])
                    if then_payload.get("markdown_template") is not None
                    else None
                ),
            )
        else:
            bodies_raw = when_payload.get("bodies")
            if bodies_raw in (None, "*"):
                bodies_a = bodies_b = "*"
            else:
                bodies_tuple = _coerce_sequence(bodies_raw)
                if bodies_tuple == "*" or len(bodies_tuple) == 0:
                    bodies_a = bodies_b = "*"
                elif len(bodies_tuple) == 1:
                    bodies_a = tuple(bodies_tuple)
                    bodies_b = "*"
                else:
                    bodies_a = (bodies_tuple[0],)
                    bodies_b = (bodies_tuple[1],)
            aspects_raw = _coerce_aspects(when_payload.get("aspect_in", "*"))
            aspects = aspects_raw if aspects_raw == "*" else tuple(aspects_raw)
            min_sev = float(when_payload.get("min_severity", 0.0))
            when = RuleWhen(
                bodiesA=bodies_a,
                bodiesB=bodies_b,
                aspects=aspects,
                min_severity=min_sev,
            )
            tags_raw = entry.get("tags", [])
            if isinstance(tags_raw, Iterable) and not isinstance(tags_raw, (str, bytes)):
                tags_tuple = tuple(str(tag) for tag in tags_raw)
            else:
                tags_tuple = (str(tags_raw),) if tags_raw else tuple()
            score_fn = str(entry.get("score_fn", "cosine^1.0"))
            then = RuleThen(
                title=str(entry.get("title", "")),
                tags=tags_tuple,
                base_score=float(entry.get("score", 0.5)),
                score_fn=score_fn,
                markdown_template=(
                    str(entry.get("text")) if entry.get("text") is not None else None
                ),
            )
        rules.append(
            Rule(
                id=str(entry.get("id")),
                scope=str(entry.get("scope", "synastry")),
                when=when,
                then=then,
            )
        )
    return rules


def _build_rulepack(data: Mapping[str, Any]) -> Rulepack:
    rulepack_id = str(data.get("rulepack") or data.get("meta", {}).get("id") or "")
    if not rulepack_id:
        raise RulepackValidationError("rulepack id is required")
    version = int(data.get("version", 1))
    profiles_raw = data.get("profiles") or {}
    if not isinstance(profiles_raw, Mapping):
        raise RulepackValidationError("profiles must be a mapping")
    rules_raw = data.get("rules")
    if not isinstance(rules_raw, Iterable):
        raise RulepackValidationError("rules must be an array")
    archetypes_raw = data.get("archetypes") or {}
    archetypes: dict[str, tuple[str, ...]] = {}
    if isinstance(archetypes_raw, Mapping):
        for name, members in archetypes_raw.items():
            if isinstance(members, Iterable) and not isinstance(members, (str, bytes)):
                archetypes[str(name)] = tuple(str(m) for m in members)
    meta = data.get("meta")
    meta_payload = meta if isinstance(meta, Mapping) else {}
    meta_dict = dict(meta_payload)
    meta_dict.setdefault("id", rulepack_id)
    meta_dict.setdefault("name", meta_dict.get("title") or rulepack_id)
    meta_dict.setdefault("title", meta_dict.get("name") or rulepack_id)
    meta_dict.setdefault("version", version)
    profiles = _coerce_profiles(profiles_raw)
    rules = _coerce_rules(rules_raw)
    return Rulepack(
        rulepack=rulepack_id,
        version=version,
        profiles=profiles,
        rules=rules,
        archetypes=archetypes,
        meta=meta_dict,
        raw=dict(data),
    )


def load_rulepack_from_data(data: dict[str, Any], *, source: str | None = None) -> LoadedRulepack:
    """Validate *data* and return a runtime rulepack."""


def load_rulepack(
    raw: str | bytes | Path | Mapping[str, Any],
    *,
    source: str | None = None,
    source_name: str | None = None,
) -> Rulepack:
    """Load and validate a rulepack from *source*."""

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


def iter_rulepack_rules(rulepack: Rulepack) -> Iterator[Rule]:
    """Yield rules from *rulepack* preserving their stored order."""

    return iter(rulepack.rules)



__all__ = [
    "RulepackValidationError",

    "iter_rulepack_rules",
    "lint_rulepack",
    "load_rulepack",
    "load_rulepack_from_data",
]
